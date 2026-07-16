#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: activate.sh --artifact-manifest FILE [--with-dev]

Run on Proxmox VE after create-vms.sh. Reconciles the rehearsal in dependency
order and never starts the app until its offline images and fake-AWS data exist.
USAGE
}

log() { printf '[activate-rehearsal %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die() { printf '[activate-rehearsal %s] ERROR: %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; exit 1; }

STATE_DIR="${FLOWFORM_REHEARSAL_STATE_DIR:-/var/lib/flowform/rehearsal}"
STATE_FILE="${STATE_DIR}/state.json"
KEY_FILE="${STATE_DIR}/ssh/id_ed25519"
KNOWN_HOSTS="${STATE_DIR}/ssh/known_hosts"
TIMEOUT="${FLOWFORM_REHEARSAL_TIMEOUT_SECONDS:-300}"
artifact_manifest=""
with_dev=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifact-manifest) artifact_manifest="${2:-}"; shift 2 ;;
    --with-dev) with_dev=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ "${EUID}" -eq 0 || "${FLOWFORM_TEST_MODE:-0}" == "1" ]] || die "run as root on the Proxmox host"
[[ -f "${STATE_FILE}" ]] || die "rehearsal state not found; run create-vms.sh first"
[[ -s "${KEY_FILE}" ]] || die "orchestration key not found: ${KEY_FILE}"
[[ -f "${artifact_manifest}" ]] || die "--artifact-manifest does not exist: ${artifact_manifest}"
for command in jq qm ssh scp ssh-keygen ssh-keyscan curl sha256sum; do
  command -v "${command}" >/dev/null 2>&1 || die "required command not found: ${command}"
done
jq -e '.schema == "flowform.rehearsal-state/1"' "${STATE_FILE}" >/dev/null || die "invalid rehearsal state"
jq -e '.schema == "flowform.rehearsal-artifact-manifest/1"' "${artifact_manifest}" >/dev/null || die "invalid artifact manifest"
image_contract="$(jq -er '.image_contract_version' "${STATE_DIR}/image-manifest.json")"
artifact_contract="$(jq -er '.image_contract_version' "${artifact_manifest}")"
[[ "${image_contract}" == "${artifact_contract}" ]] \
  || die "artifact contract ${artifact_contract} is incompatible with image contract ${image_contract}"

artifact_dir="$(cd -- "$(dirname -- "${artifact_manifest}")" && pwd)"
archive_name="$(jq -er '.archive.file' "${artifact_manifest}")"
archive="${artifact_dir}/${archive_name}"
checksums="${artifact_dir}/SHA256SUMS"
[[ -f "${archive}" && -f "${checksums}" ]] || die "artifact set is incomplete in ${artifact_dir}"
(
  cd "${artifact_dir}"
  sha256sum --check --status SHA256SUMS
) || die "artifact checksum verification failed"
release="$(jq -er '.release' "${artifact_manifest}")"
backend_image="$(jq -er '.images.backend' "${artifact_manifest}")"
backend_tag="${backend_image##*:}"

ssh_options=(
  -i "${KEY_FILE}"
  -o BatchMode=yes
  -o ConnectTimeout=5
  -o UserKnownHostsFile="${KNOWN_HOSTS}"
  -o StrictHostKeyChecking=yes
)

vm_status() { qm status "$1" | awk '{print $2}'; }
start_vm() {
  local vmid="$1"
  if [[ "$(vm_status "${vmid}")" != "running" ]]; then
    log "starting VM ${vmid}"
    qm start "${vmid}"
  else
    log "VM ${vmid} already running"
  fi
}

wait_guest_agent() {
  local vmid="$1" deadline=$((SECONDS + TIMEOUT))
  until qm guest ping "${vmid}" >/dev/null 2>&1; do
    (( SECONDS < deadline )) || die "VM ${vmid} guest agent timeout after ${TIMEOUT}s"
    sleep 2
  done
}

refresh_host_key() {
  local ip="$1" deadline=$((SECONDS + TIMEOUT))
  touch "${KNOWN_HOSTS}"
  chmod 0600 "${KNOWN_HOSTS}"
  ssh-keygen -q -f "${KNOWN_HOSTS}" -R "${ip}" >/dev/null 2>&1 || true
  until ssh-keyscan -T 5 -H "${ip}" >> "${KNOWN_HOSTS}" 2>/dev/null; do
    (( SECONDS < deadline )) || die "SSH host key timeout for ${ip}"
    sleep 2
  done
}

remote() {
  local ip="$1"; shift
  ssh "${ssh_options[@]}" "flowform@${ip}" "$@"
}

wait_cloud_init() {
  local ip="$1"
  remote "${ip}" sudo cloud-init status --wait >/dev/null \
    || die "cloud-init failed on ${ip}; inspect /var/log/cloud-init-output.log"
}

wait_http() {
  local description="$1" url="$2"; shift 2
  local deadline=$((SECONDS + TIMEOUT))
  until curl -fsS --max-time 5 "$@" "${url}" >/dev/null 2>&1; do
    (( SECONDS < deadline )) || die "${description} timeout after ${TIMEOUT}s (${url})"
    sleep 2
  done
}

# Foundation: internet-connected proxy first.
start_vm 210
wait_guest_agent 210
refresh_host_key 10.10.10.10
wait_cloud_init 10.10.10.10
remote 10.10.10.10 "sudo systemctl is-active --quiet docker && sudo ss -lnt | grep -q ':3128 '" \
  || die "proxy Docker/Squid is not ready"

# Offline fixtures host: cloud-init prepares files and units, activation supplies images.
start_vm 230
wait_guest_agent 230
refresh_host_key 10.10.10.30
wait_cloud_init 10.10.10.30
remote 10.10.10.30 sudo install -d -m 0700 /opt/flowform/rehearsal/artifacts
scp "${ssh_options[@]}" "${archive}" "${artifact_manifest}" "${checksums}" \
  flowform@10.10.10.30:/tmp/
remote 10.10.10.30 \
  "cd /tmp && sha256sum --check $(basename "${checksums}") && sudo docker load --input /tmp/${archive_name} && sudo mv /tmp/${archive_name} /tmp/$(basename "${artifact_manifest}") /tmp/$(basename "${checksums}") /opt/flowform/rehearsal/artifacts/"

remote 10.10.10.30 sudo systemctl start flowform-registry.service
wait_http registry http://10.10.10.30:5000/v2/
remote 10.10.10.30 sudo systemctl start flowform-localstack.service
wait_http LocalStack http://10.10.10.30:4566/_localstack/health
remote 10.10.10.30 sudo systemctl start flowform-tls-shim.service
wait_http 'TLS shim' https://ssm.localstack.test/_localstack/health \
  --insecure --resolve ssm.localstack.test:443:10.10.10.30

log "populating rehearsal registry"
remote 10.10.10.30 \
  "sudo docker tag postgres:17 localhost:5000/postgres:17 && sudo docker push localhost:5000/postgres:17 && sudo docker tag '${backend_image}' 'localhost:5000/flowform-backend:${backend_tag}' && sudo docker push 'localhost:5000/flowform-backend:${backend_tag}'"
remote 10.10.10.30 \
  "sudo env AWS_ENDPOINT_URL=http://127.0.0.1:4566 BACKEND_IMAGE='10.10.10.30:5000/flowform-backend:${backend_tag}' /opt/flowform/rehearsal/seed-localstack.sh"

# Reconcile the proxy after seeding, then activate the isolated app.
remote 10.10.10.10 sudo /opt/flowform/scripts/run-bootstrap-proxy.sh
start_vm 220
wait_guest_agent 220
refresh_host_key 10.10.10.20
wait_cloud_init 10.10.10.20
remote 10.10.10.20 sudo /opt/flowform/scripts/run-bootstrap-app.sh
wait_http 'backend readiness' http://10.10.10.20:5000/api/v1/system/health/ready
wait_http 'proxy readiness' https://api.localstack.test/api/v1/system/health/ready \
  --insecure --resolve api.localstack.test:443:10.10.10.10

if [[ "${with_dev}" == "1" ]]; then
  jq -e '.vmids | index(240)' "${STATE_FILE}" >/dev/null || die "VM 240 was not created; rerun create-vms.sh --with-dev"
  start_vm 240
  wait_guest_agent 240
  refresh_host_key 10.10.10.40
  wait_cloud_init 10.10.10.40
fi

install -m 0600 "${artifact_manifest}" "${STATE_DIR}/artifact-manifest.json"
tmp="$(mktemp "${STATE_FILE}.tmp.XXXXXX")"
jq --arg release "${release}" \
  '.status = "active" | .release = $release | .activated_at = (now | todateiso8601)' \
  "${STATE_FILE}" > "${tmp}"
mv "${tmp}" "${STATE_FILE}"
chmod 0600 "${STATE_FILE}"
log "rehearsal ${release:0:12} is active and healthy"
