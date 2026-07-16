#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: prepare-proxmox-source.sh --source-vmid ID --upload PVE_SSH_TARGET [options]

Downloads and checksum-verifies the pinned Amazon Linux KVM image, uploads it
to a Proxmox host, and invokes the canonical source-template importer there.

Required environment:
  PROXMOX_PACKER_SSH_PRIVATE_KEY_FILE  Temporary Packer build private key.
                                       Its .pub file must exist.

Options:
  --source-vmid ID     Required source-template VMID
  --upload TARGET      Required SSH target, for example root@pve.example.lan
  --storage NAME       Proxmox storage (default: ZFS-RAIDZ)
  --bridge NAME        Build bridge (default: vmbr0)
  --cache-dir DIR      Download cache (default: infra/.generated/image-factory/cache)
  --replace            Replace the source VMID if it already exists
  --help               Show this help
USAGE
}

log() { printf '[prepare-proxmox-source] %s\n' "$*"; }
die() { printf '[prepare-proxmox-source] ERROR: %s\n' "$*" >&2; exit 1; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
LOCK_FILE="${SCRIPT_DIR}/sources/amazon-linux-2023.lock"
# shellcheck source=/dev/null
. "${LOCK_FILE}"

source_vmid=""
upload=""
storage="${PROXMOX_STORAGE:-ZFS-RAIDZ}"
bridge="${PROXMOX_BUILD_BRIDGE:-vmbr0}"
cache_dir="${REPO_ROOT}/infra/.generated/image-factory/cache"
replace=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source-vmid) source_vmid="${2:-}"; shift 2 ;;
    --upload) upload="${2:-}"; shift 2 ;;
    --storage) storage="${2:-}"; shift 2 ;;
    --bridge) bridge="${2:-}"; shift 2 ;;
    --cache-dir) cache_dir="${2:-}"; shift 2 ;;
    --replace) replace=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ "${source_vmid}" =~ ^[1-9][0-9]{2,8}$ ]] || die "--source-vmid must be a valid numeric VMID"
[[ -n "${upload}" ]] || die "--upload is required"
private_key="${PROXMOX_PACKER_SSH_PRIVATE_KEY_FILE:-}"
[[ -s "${private_key}" ]] || die "set PROXMOX_PACKER_SSH_PRIVATE_KEY_FILE to a readable private key"
[[ -s "${private_key}.pub" ]] || die "matching public key not found: ${private_key}.pub"
for command in curl sha256sum ssh scp; do
  command -v "${command}" >/dev/null 2>&1 || die "required command not found: ${command}"
done

install -d -m 0750 "${cache_dir}"
image="${cache_dir}/${AL2023_FILENAME}"
if [[ ! -f "${image}" ]]; then
  log "downloading Amazon Linux ${AL2023_VERSION}"
  curl -fL --retry 3 --output "${image}.part" "${AL2023_URL}"
  mv "${image}.part" "${image}"
fi
printf '%s  %s\n' "${AL2023_SHA256}" "${image}" | sha256sum --check --status \
  || die "checksum mismatch for ${image}"
log "verified ${AL2023_FILENAME} (${AL2023_SHA256})"

remote_dir="/var/lib/flowform/image-factory/source/${AL2023_VERSION}"
ssh "${upload}" install -d -m 0700 "${remote_dir}"
scp "${image}" "${private_key}.pub" \
  "${SCRIPT_DIR}/../platforms/proxmox/import-source-image.sh" \
  "${upload}:${remote_dir}/"

remote_args=(
  --source-vmid "${source_vmid}"
  --image "${remote_dir}/${AL2023_FILENAME}"
  --ssh-public-key "${remote_dir}/$(basename "${private_key}").pub"
  --name "${AL2023_SOURCE_TEMPLATE_NAME}"
  --storage "${storage}"
  --bridge "${bridge}"
)
[[ "${replace}" == "1" ]] && remote_args+=(--replace)
ssh "${upload}" "${remote_dir}/import-source-image.sh" "${remote_args[@]}"
log "source template ${source_vmid} prepared on ${upload}"
