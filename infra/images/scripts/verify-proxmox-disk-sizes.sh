#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
vmids=()

usage() {
  cat <<'USAGE'
Usage: verify-proxmox-disk-sizes.sh [--env-file PATH] [VMID...]

Report the downloaded QCOW2 file/virtual sizes and validate Proxmox virtual
disk sizes against PROXMOX_DISK_MAX_SIZE. With no VMIDs, checks the source,
golden, LocalStack fixture, and DB fixture templates (8999–9002 by default).
USAGE
}

die() {
  printf '[verify-proxmox-disk-sizes] ERROR: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      [[ $# -ge 2 ]] || die "--env-file requires a path"
      ENV_FILE="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      [[ "$1" =~ ^[0-9]+$ ]] || die "VMID must be numeric: $1"
      vmids+=("$1")
      shift
      ;;
  esac
done

[[ -f "${ENV_FILE}" ]] || die "environment file not found: ${ENV_FILE}"
set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

required=(
  PROXMOX_SSH_IDENTITY_FILE PROXMOX_SSH_TARGET PROXMOX_SSH_PORT
  PROXMOX_SOURCE_VMID PROXMOX_IMAGE_CACHE_DIR PROXMOX_DISK_MAX_SIZE
  AL2023_IMAGE_FILENAME
)
for variable_name in "${required[@]}"; do
  [[ -n "${!variable_name:-}" ]] || die "${variable_name} is empty in ${ENV_FILE}"
done
[[ "${PROXMOX_DISK_MAX_SIZE}" =~ ^[1-9][0-9]*[KMGT]$ ]] \
  || die "PROXMOX_DISK_MAX_SIZE must be an IEC size such as 25G"

if (( ${#vmids[@]} == 0 )); then
  vmids=("${PROXMOX_SOURCE_VMID}" 9000 9001 9002)
fi

ssh -i "${PROXMOX_SSH_IDENTITY_FILE}" \
  -p "${PROXMOX_SSH_PORT}" \
  -o BatchMode=yes \
  -o ConnectTimeout=10 \
  "${PROXMOX_SSH_TARGET}" \
  bash -s -- \
  "${PROXMOX_IMAGE_CACHE_DIR}/${AL2023_IMAGE_FILENAME}" \
  "${PROXMOX_DISK_MAX_SIZE}" \
  "${vmids[@]}" <<'REMOTE'
set -Eeuo pipefail

image_path="$1"
max_size="$2"
shift 2
max_bytes="$(numfmt --from=iec "${max_size}")"

[[ -f "${image_path}" ]] || {
  echo "downloaded image missing: ${image_path}" >&2
  exit 1
}

image_file_bytes="$(stat -c %s "${image_path}")"
image_virtual_bytes="$(qemu-img info --output=json "${image_path}" \
  | sed -n 's/^[[:space:]]*"virtual-size":[[:space:]]*\([0-9][0-9]*\),\{0,1\}$/\1/p' \
  | tail -n 1)"
[[ "${image_virtual_bytes}" =~ ^[0-9]+$ ]] || {
  echo "could not read QCOW2 virtual size: ${image_path}" >&2
  exit 1
}

printf 'downloaded-qcow2\tfile-bytes=%s\tvirtual-bytes=%s\tvirtual=%s\tmaximum=%s\n' \
  "${image_file_bytes}" "${image_virtual_bytes}" \
  "$(numfmt --to=iec --suffix=B "${image_virtual_bytes}")" "${max_size}"
(( image_virtual_bytes <= max_bytes )) || {
  echo "downloaded QCOW2 exceeds maximum ${max_size}" >&2
  exit 1
}

failed=0
for vmid in "$@"; do
  if ! qm status "${vmid}" >/dev/null 2>&1; then
    printf 'vmid=%s\tabsent\n' "${vmid}"
    failed=1
    continue
  fi
  config="$(qm config "${vmid}")"
  name="$(sed -n 's/^name: //p' <<<"${config}")"
  disk="$(sed -n 's/^scsi0: .*size=\([^,]*\).*/\1/p' <<<"${config}")"
  [[ -n "${disk}" ]] || {
    printf 'vmid=%s\tname=%s\tdisk=unreadable\n' "${vmid}" "${name}"
    failed=1
    continue
  }
  disk_bytes="$(numfmt --from=iec "${disk}")"
  printf 'vmid=%s\tname=%s\tvirtual=%s\tvirtual-bytes=%s\tmaximum=%s\n' \
    "${vmid}" "${name}" "${disk}" "${disk_bytes}" "${max_size}"
  if (( disk_bytes > max_bytes )); then
    printf 'vmid=%s exceeds maximum %s; rebuild instead of shrinking in place\n' \
      "${vmid}" "${max_size}" >&2
    failed=1
  fi
done

exit "${failed}"
REMOTE
