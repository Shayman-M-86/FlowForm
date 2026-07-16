#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROXMOX_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_ENV_FILE="${PROXMOX_DIR}/.env"
BOOTSTRAP_FILE="${SCRIPT_DIR}/source-bootstrap.user-data.yaml"

ENV_FILE="${DEFAULT_ENV_FILE}"
MODE="preflight"
REPLACE="0"

usage() {
  cat <<'USAGE'
Usage: 01-prepare-proxmox-source.sh [options]

Prepare the cloud-init-enabled Amazon Linux source template used by the
FlowForm Packer Proxmox clone builder.

The command is non-mutating by default. Copy .env.example to .env, fill in the
Proxmox values, and run the script once for preflight. Pass --apply only after
preflight succeeds.

Options:
  --env-file PATH  Load configuration from PATH instead of .env beside script.
  --apply          Download/import/configure and convert the source template.
  --replace        With --apply, replace an existing mismatched source VMID.
  --help           Show this help.

Examples:
  cp infra/images/proxmox/.env.example infra/images/proxmox/.env
  infra/images/proxmox/provisioning/01-prepare-proxmox-source.sh
  infra/images/proxmox/provisioning/01-prepare-proxmox-source.sh --apply
USAGE
}

die() {
  printf '[prepare-proxmox-source] ERROR: %s\n' "$*" >&2
  exit 1
}

log() {
  printf '[prepare-proxmox-source] %s\n' "$*"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      [[ $# -ge 2 ]] || die "--env-file requires a path"
      ENV_FILE="$2"
      shift 2
      ;;
    --apply)
      MODE="apply"
      shift
      ;;
    --replace)
      REPLACE="1"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ "${REPLACE}" == "0" || "${MODE}" == "apply" ]] \
  || die "--replace is only valid with --apply"
[[ -f "${ENV_FILE}" ]] \
  || die "environment file not found: ${ENV_FILE} (copy ${PROXMOX_DIR}/.env.example to ${DEFAULT_ENV_FILE})"
[[ -f "${BOOTSTRAP_FILE}" ]] || die "bootstrap user-data missing: ${BOOTSTRAP_FILE}"

set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

required_vars=(
  PROXMOX_SSH_IDENTITY_FILE
  PROXMOX_SSH_TARGET
  PROXMOX_SSH_PORT
  PROXMOX_NODE
  PROXMOX_SOURCE_VMID
  PROXMOX_SOURCE_TEMPLATE_NAME
  PROXMOX_STORAGE_POOL
  PROXMOX_SNIPPET_STORAGE
  PROXMOX_SNIPPET_DIR
  PROXMOX_NETWORK_BRIDGE
  PROXMOX_CPU_TYPE
  PROXMOX_SOURCE_DISK_SIZE
  PROXMOX_SOURCE_MEMORY
  PROXMOX_SOURCE_CORES
  PROXMOX_BUILD_TIMEOUT_SECONDS
  PROXMOX_IMAGE_CACHE_DIR
  AL2023_RELEASE
  AL2023_IMAGE_FILENAME
  AL2023_IMAGE_URL
  AL2023_IMAGE_SHA256
)

for variable_name in "${required_vars[@]}"; do
  [[ -n "${!variable_name:-}" ]] || die "${variable_name} is empty in ${ENV_FILE}"
done

validate_simple_name() {
  local variable_name="$1"
  local value="${!variable_name}"
  [[ "${value}" =~ ^[A-Za-z0-9._:-]+$ ]] \
    || die "${variable_name} contains unsupported characters: ${value}"
}

validate_path() {
  local variable_name="$1"
  local value="${!variable_name}"
  [[ "${value}" =~ ^/[A-Za-z0-9._/-]+$ ]] \
    || die "${variable_name} must be an absolute path without whitespace: ${value}"
}

for variable_name in \
  PROXMOX_NODE PROXMOX_SOURCE_TEMPLATE_NAME PROXMOX_STORAGE_POOL \
  PROXMOX_SNIPPET_STORAGE PROXMOX_NETWORK_BRIDGE PROXMOX_CPU_TYPE AL2023_RELEASE \
  AL2023_IMAGE_FILENAME; do
  validate_simple_name "${variable_name}"
done
validate_path PROXMOX_SNIPPET_DIR
validate_path PROXMOX_IMAGE_CACHE_DIR
validate_path PROXMOX_SSH_IDENTITY_FILE
[[ -r "${PROXMOX_SSH_IDENTITY_FILE}" ]] \
  || die "PROXMOX_SSH_IDENTITY_FILE is not readable: ${PROXMOX_SSH_IDENTITY_FILE}"

[[ "${PROXMOX_SSH_PORT}" =~ ^[0-9]+$ ]] || die "PROXMOX_SSH_PORT must be numeric"
[[ "${PROXMOX_SOURCE_VMID}" =~ ^[0-9]+$ ]] || die "PROXMOX_SOURCE_VMID must be numeric"
(( PROXMOX_SOURCE_VMID >= 100 && PROXMOX_SOURCE_VMID <= 999999999 )) \
  || die "PROXMOX_SOURCE_VMID must be between 100 and 999999999"
[[ "${PROXMOX_SOURCE_MEMORY}" =~ ^[0-9]+$ ]] || die "PROXMOX_SOURCE_MEMORY must be numeric"
[[ "${PROXMOX_SOURCE_CORES}" =~ ^[0-9]+$ ]] || die "PROXMOX_SOURCE_CORES must be numeric"
[[ "${PROXMOX_BUILD_TIMEOUT_SECONDS}" =~ ^[0-9]+$ ]] \
  || die "PROXMOX_BUILD_TIMEOUT_SECONDS must be numeric"
[[ "${PROXMOX_SOURCE_DISK_SIZE}" =~ ^[1-9][0-9]*[KMGT]$ ]] \
  || die "PROXMOX_SOURCE_DISK_SIZE must look like 16G"
url_pattern='^https://[A-Za-z0-9._~:/?%&=+-]+$'
[[ "${AL2023_IMAGE_URL}" =~ ${url_pattern} ]] \
  || die "AL2023_IMAGE_URL must be an HTTPS URL without shell metacharacters"
[[ "${AL2023_IMAGE_SHA256}" =~ ^[0-9a-fA-F]{64}$ ]] \
  || die "AL2023_IMAGE_SHA256 must contain exactly 64 hexadecimal characters"
[[ "${AL2023_IMAGE_FILENAME}" == al2023-kvm-* ]] \
  || die "AL2023_IMAGE_FILENAME is not an Amazon Linux 2023 KVM image"

SSH_BIN="${PROXMOX_SSH_BIN:-ssh}"
command -v "${SSH_BIN}" >/dev/null 2>&1 || die "SSH command not found: ${SSH_BIN}"
command -v base64 >/dev/null 2>&1 || die "base64 is required locally"

BOOTSTRAP_B64="$(base64 -w 0 "${BOOTSTRAP_FILE}")"
ssh_args=(
  -i "${PROXMOX_SSH_IDENTITY_FILE}"
  -p "${PROXMOX_SSH_PORT}"
  -o BatchMode=yes
  -o ConnectTimeout=10
  "${PROXMOX_SSH_TARGET}"
  bash -s --
  "${MODE}"
  "${REPLACE}"
  "${PROXMOX_NODE}"
  "${PROXMOX_SOURCE_VMID}"
  "${PROXMOX_SOURCE_TEMPLATE_NAME}"
  "${PROXMOX_STORAGE_POOL}"
  "${PROXMOX_SNIPPET_STORAGE}"
  "${PROXMOX_SNIPPET_DIR}"
  "${PROXMOX_NETWORK_BRIDGE}"
  "${PROXMOX_CPU_TYPE}"
  "${PROXMOX_SOURCE_DISK_SIZE}"
  "${PROXMOX_SOURCE_MEMORY}"
  "${PROXMOX_SOURCE_CORES}"
  "${PROXMOX_BUILD_TIMEOUT_SECONDS}"
  "${PROXMOX_IMAGE_CACHE_DIR}"
  "${AL2023_RELEASE}"
  "${AL2023_IMAGE_FILENAME}"
  "${AL2023_IMAGE_URL}"
  "${AL2023_IMAGE_SHA256,,}"
  "${BOOTSTRAP_B64}"
)

log "mode=${MODE} env=${ENV_FILE} target=${PROXMOX_SSH_TARGET} source-vmid=${PROXMOX_SOURCE_VMID}"

"${SSH_BIN}" "${ssh_args[@]}" <<'REMOTE_SCRIPT'
set -Eeuo pipefail
trap 'exit 130' HUP INT TERM

mode="$1"
replace="$2"
node="$3"
vmid="$4"
template_name="$5"
storage_pool="$6"
snippet_storage="$7"
snippet_dir="$8"
network_bridge="$9"
cpu_type="${10}"
disk_size="${11}"
memory="${12}"
cores="${13}"
build_timeout="${14}"
image_cache_dir="${15}"
al2023_release="${16}"
image_filename="${17}"
image_url="${18}"
image_sha256="${19}"
bootstrap_b64="${20}"

prefix='[prepare-proxmox-source:remote]'
description="FlowForm Packer source; al2023=${al2023_release}; cpu=${cpu_type}; sha256=${image_sha256}"
snippet_name="flowform-packer-source-${vmid}.user-data.yaml"
snippet_path="${snippet_dir}/${snippet_name}"
snippet_ref="${snippet_storage}:snippets/${snippet_name}"
image_path="${image_cache_dir}/${image_filename}"

log() {
  printf '%s %s\n' "${prefix}" "$*"
}

die() {
  printf '%s ERROR: %s\n' "${prefix}" "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found on Proxmox host: $1"
}

for command_name in awk base64 curl date grep install ip mv numfmt qm pvesh pvesm rm sed sha256sum sleep virt-customize; do
  require_command "${command_name}"
done

pvesh get "/nodes/${node}/status" >/dev/null \
  || die "Proxmox node not found or inaccessible: ${node}"
ip link show "${network_bridge}" >/dev/null 2>&1 \
  || die "network bridge not found: ${network_bridge}"
pvesm status | awk -v storage="${storage_pool}" \
  'NR > 1 && $1 == storage && $3 == "active" { found=1 } END { exit !found }' \
  || die "VM storage is missing or inactive: ${storage_pool}"
pvesm status | awk -v storage="${snippet_storage}" \
  'NR > 1 && $1 == storage && $3 == "active" { found=1 } END { exit !found }' \
  || die "snippet storage is missing or inactive: ${snippet_storage}"

snippets_enabled=0
if pvesm status --content snippets 2>/dev/null | awk -v storage="${snippet_storage}" \
  'NR > 1 && $1 == storage { found=1 } END { exit !found }'; then
  snippets_enabled=1
fi

matching_existing=0
if qm status "${vmid}" >/dev/null 2>&1; then
  existing_config="$(qm config "${vmid}")"
  if grep -qx 'template: 1' <<<"${existing_config}" \
    && grep -qx "name: ${template_name}" <<<"${existing_config}" \
    && grep -Fqx "description: ${description}" <<<"${existing_config}"; then
    matching_existing=1
  elif [[ "${replace}" != "1" ]]; then
    die "VMID ${vmid} already exists but does not match the pinned source template; inspect it or rerun with --apply --replace"
  else
    log "VMID ${vmid} exists and will be replaced"
  fi
fi

conflicting_vmid="$(qm list | awk -v name="${template_name}" -v vmid="${vmid}" \
  'NR > 1 && $2 == name && $1 != vmid { print $1; exit }')"
[[ -z "${conflicting_vmid}" ]] \
  || die "template name ${template_name} already belongs to VMID ${conflicting_vmid}"

curl -fsSIL --max-time 30 "${image_url}" >/dev/null \
  || die "pinned image URL is not reachable from the Proxmox host: ${image_url}"

if [[ "${matching_existing}" == "1" ]]; then
  log "matching source template ${vmid} (${template_name}) already exists; no changes needed"
  exit 0
fi

if [[ "${mode}" == "preflight" ]]; then
  if [[ "${snippets_enabled}" == "1" ]]; then
    log "snippet content is enabled on ${snippet_storage}"
  else
    log "snippet content is not enabled on ${snippet_storage}; --apply will append it while preserving existing content"
  fi
  log "preflight OK: --apply can create source template ${vmid} (${template_name})"
  exit 0
fi

[[ "${mode}" == "apply" ]] || die "internal error: unsupported mode ${mode}"

if [[ "${snippets_enabled}" != "1" ]]; then
  storage_json="$(pvesh get "/storage/${snippet_storage}" --output-format json)"
  current_content="$(sed -n 's/.*"content":"\([^"]*\)".*/\1/p' <<<"${storage_json}")"
  [[ -n "${current_content}" ]] || die "could not read current content types for ${snippet_storage}"
  case ",${current_content}," in
    *,snippets,*) ;;
    *)
      log "enabling snippets on ${snippet_storage}"
      pvesm set "${snippet_storage}" --content "${current_content},snippets" >/dev/null
      ;;
  esac
fi

if qm status "${vmid}" >/dev/null 2>&1; then
  log "destroying explicitly replaceable VMID ${vmid}"
  qm stop "${vmid}" >/dev/null 2>&1 || true
  qm destroy "${vmid}" --purge
fi

install -d -m 0755 "${image_cache_dir}" "${snippet_dir}"
if [[ -f "${image_path}" ]] \
  && printf '%s  %s\n' "${image_sha256}" "${image_path}" | sha256sum -c - >/dev/null 2>&1; then
  log "using checksum-verified cached image ${image_path}"
else
  log "downloading pinned Amazon Linux ${al2023_release} image"
  rm -f "${image_path}.tmp"
  curl -fL --retry 3 --retry-delay 2 --output "${image_path}.tmp" "${image_url}"
  printf '%s  %s\n' "${image_sha256}" "${image_path}.tmp" | sha256sum -c - >/dev/null \
    || die "checksum verification failed for ${image_path}.tmp"
  mv -f "${image_path}.tmp" "${image_path}"
fi

printf '%s' "${bootstrap_b64}" | base64 --decode >"${snippet_path}.tmp"
install -m 0644 "${snippet_path}.tmp" "${snippet_path}"
rm -f "${snippet_path}.tmp"

log "creating source builder VM ${vmid} (${template_name})"
qm create "${vmid}" \
  --name "${template_name}" \
  --description "${description}" \
  --memory "${memory}" \
  --cores "${cores}" \
  --cpu "${cpu_type}" \
  --net0 "virtio,bridge=${network_bridge}" \
  --scsihw virtio-scsi-single \
  --ostype l26 \
  --agent enabled=0 \
  --serial0 socket \
  --vga serial0

log "importing source disk into ${storage_pool}"
qm importdisk "${vmid}" "${image_path}" "${storage_pool}" >/dev/null
imported_volume="$(qm config "${vmid}" | awk -F': ' '$1 == "unused0" { print $2; exit }')"
[[ -n "${imported_volume}" ]] || die "could not identify the imported disk for VMID ${vmid}"
qm set "${vmid}" --scsi0 "${imported_volume}" >/dev/null
qm set "${vmid}" --ide2 "${storage_pool}:cloudinit" >/dev/null
qm set "${vmid}" --boot order=scsi0 >/dev/null
current_disk_size="$(qm config "${vmid}" | sed -n 's/^scsi0: .*size=\([^,]*\).*/\1/p')"
[[ -n "${current_disk_size}" ]] || die "could not read the imported disk size for VMID ${vmid}"
current_disk_bytes="$(numfmt --from=iec "${current_disk_size}")"
requested_disk_bytes="$(numfmt --from=iec "${disk_size}")"
if (( requested_disk_bytes > current_disk_bytes )); then
  log "growing source disk from ${current_disk_size} to ${disk_size}"
  qm disk resize "${vmid}" scsi0 "${disk_size}"
else
  log "source disk is ${current_disk_size}; requested ${disk_size} does not require growth"
fi
qm set "${vmid}" --ipconfig0 ip=dhcp >/dev/null
qm set "${vmid}" --ciuser ec2-user >/dev/null
qm set "${vmid}" --cicustom "user=${snippet_ref}" >/dev/null

status_of() {
  qm status "${vmid}" 2>/dev/null | awk '{ print $2 }'
}

wait_for_status() {
  local expected="$1"
  local timeout="$2"
  local deadline=$(( $(date +%s) + timeout ))
  while [[ "$(status_of)" != "${expected}" ]]; do
    (( $(date +%s) < deadline )) \
      || die "timeout waiting for VMID ${vmid} to become ${expected}"
    log "waiting for VMID ${vmid} to become ${expected}"
    sleep 5
  done
}

log "starting bootstrap boot; cloud-init will validate, generalize, and power off"
qm start "${vmid}"
wait_for_status running 60
wait_for_status stopped "${build_timeout}"

log "generalizing the stopped source disk"
source_disk_path="$(pvesm path "${imported_volume}")"
virt-customize -a "${source_disk_path}" \
  --run-command 'cloud-init clean --logs' \
  --run-command 'rm -f /etc/ssh/ssh_host_*' \
  --run-command 'truncate -s 0 /etc/machine-id' \
  --run-command 'rm -f /var/lib/dbus/machine-id'

qm set "${vmid}" --delete cicustom >/dev/null
qm set "${vmid}" --description "${description}" >/dev/null
qm set "${vmid}" --tags 'flowform;packer-source;al2023' >/dev/null
log "converting VMID ${vmid} to template"
qm template "${vmid}"
qm config "${vmid}" | grep -qx 'template: 1' \
  || die "VMID ${vmid} was not converted to a template"

log "source template ready: ${vmid} (${template_name})"
REMOTE_SCRIPT

if [[ "${MODE}" == "preflight" ]]; then
  log "preflight complete; no Proxmox resources were changed"
else
  log "source-template preparation complete"
fi
