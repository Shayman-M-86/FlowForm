#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: verify.sh

Run on Proxmox VE after activation. Verifies topology, services, Compose layers,
fake-AWS access, registry population, and the app VM's lack of a default route.
USAGE
}

log() { printf '[verify-rehearsal] %s\n' "$*"; }
die() { printf '[verify-rehearsal] ERROR: %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

STATE_DIR="${FLOWFORM_REHEARSAL_STATE_DIR:-/var/lib/flowform/rehearsal}"
STATE_FILE="${STATE_DIR}/state.json"
KEY_FILE="${STATE_DIR}/ssh/id_ed25519"
KNOWN_HOSTS="${STATE_DIR}/ssh/known_hosts"
[[ "${EUID}" -eq 0 || "${FLOWFORM_TEST_MODE:-0}" == "1" ]] || die "run as root on the Proxmox host"
for command in jq qm ssh curl; do command -v "${command}" >/dev/null 2>&1 || die "missing ${command}"; done
jq -e '.schema == "flowform.rehearsal-state/1" and .status == "active"' "${STATE_FILE}" >/dev/null \
  || die "rehearsal is not recorded as active"
ssh_options=(-i "${KEY_FILE}" -o BatchMode=yes -o UserKnownHostsFile="${KNOWN_HOSTS}" -o StrictHostKeyChecking=yes)
remote() { local ip="$1"; shift; ssh "${ssh_options[@]}" "flowform@${ip}" "$@"; }

for vmid in 210 220 230; do
  [[ "$(qm status "${vmid}" | awk '{print $2}')" == "running" ]] || die "VM ${vmid} is not running"
done
qm config 210 | grep -q 'bridge=vmbr10' || die "proxy private NIC missing"
qm config 220 | grep -q 'ip=10.10.10.20/24' || die "app private IP mismatch"
qm config 230 | grep -q 'ip=10.10.10.30/24' || die "fixtures private IP mismatch"

remote 10.10.10.30 "sudo systemctl is-active --quiet flowform-registry flowform-localstack flowform-tls-shim"
curl -fsS http://10.10.10.30:5000/v2/_catalog | grep -q 'flowform-backend' || die "backend absent from registry"
curl -fsS http://10.10.10.30:4566/_localstack/health >/dev/null || die "LocalStack is unhealthy"

remote 10.10.10.20 \
  "sudo docker compose --env-file /opt/flowform/backend.env -f /opt/flowform/repo/infra/runtime/compose/docker-compose.app.yml -f /opt/flowform/repo/infra/environments/rehearsal/compose/docker-compose.app.rehearsal.yml config --services | grep -qx core-db"
remote 10.10.10.20 \
  "sudo docker compose --env-file /opt/flowform/backend.env -f /opt/flowform/repo/infra/runtime/compose/docker-compose.app.yml -f /opt/flowform/repo/infra/environments/rehearsal/compose/docker-compose.app.rehearsal.yml config --services | grep -qx response-db"

curl -fsS http://10.10.10.20:5000/api/v1/system/health/ready >/dev/null || die "backend readiness failed"
curl -kfsS --resolve api.localstack.test:443:10.10.10.10 \
  https://api.localstack.test/api/v1/system/health/ready >/dev/null || die "proxy readiness failed"
remote 10.10.10.20 "! ip route show default | grep -q ." || die "app VM unexpectedly has a default route"
remote 10.10.10.20 "! curl --noproxy '*' -fsS --max-time 5 https://1.1.1.1/ >/dev/null 2>&1" \
  || die "app VM unexpectedly reached the public internet directly"
remote 10.10.10.20 \
  "set -a; . /etc/flowform/bootstrap-app.env; set +a; aws ssm get-parameters-by-path --path /flowform/nonprod/backend/ --recursive --region ap-southeast-2 >/dev/null"

log "topology, dependencies, Compose layers, readiness, fake-AWS path, and isolation verified"
