#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: build-proxmox-template.sh --vmid ID --var-file FILE --verify-on PVE_SSH_TARGET [options]

Validates Proxmox access and builds an immutable FlowForm template candidate.

Required environment:
  PROXMOX_TOKEN_SECRET_FILE              Root/user-readable 0600 token file
  PROXMOX_PACKER_SSH_PRIVATE_KEY_FILE    Build SSH private key used by Packer

Options:
  --vmid ID          Required unused output VMID
  --var-file FILE    Required non-secret Packer variables file
  --validate-only    Run preflight and full Packer validation without building
  --verify-on TARGET Run the required smoke clone on this Proxmox SSH target
  --output-dir DIR   Generated manifest directory
  --help             Show this help
USAGE
}

log() { printf '[build-proxmox-template] %s\n' "$*"; }
die() { printf '[build-proxmox-template] ERROR: %s\n' "$*" >&2; exit 1; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
PACKER_DIR="${SCRIPT_DIR}/packer"
SOURCE_LOCK="${SCRIPT_DIR}/sources/amazon-linux-2023.lock"
# shellcheck source=/dev/null
. "${SOURCE_LOCK}"

vmid=""
var_file=""
validate_only=0
output_dir=""
verify_on=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vmid) vmid="${2:-}"; shift 2 ;;
    --var-file) var_file="${2:-}"; shift 2 ;;
    --validate-only) validate_only=1; shift ;;
    --verify-on) verify_on="${2:-}"; shift 2 ;;
    --output-dir) output_dir="${2:-}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ "${vmid}" =~ ^[1-9][0-9]{2,8}$ ]] || die "--vmid must be a valid numeric VMID"
[[ -f "${var_file}" ]] || die "--var-file does not exist: ${var_file}"
if [[ "${validate_only}" != "1" ]]; then
  [[ -n "${verify_on}" ]] || die "--verify-on is required for a build; unverified candidates are not selectable"
fi
var_file="$(cd -- "$(dirname -- "${var_file}")" && pwd)/$(basename -- "${var_file}")"
output_dir="${output_dir:-${REPO_ROOT}/infra/.generated/image-factory/proxmox/${vmid}}"

token_file="${PROXMOX_TOKEN_SECRET_FILE:-}"
private_key="${PROXMOX_PACKER_SSH_PRIVATE_KEY_FILE:-}"
[[ -s "${token_file}" ]] || die "set PROXMOX_TOKEN_SECRET_FILE to the one-time token secret file"
[[ -s "${private_key}" ]] || die "set PROXMOX_PACKER_SSH_PRIVATE_KEY_FILE to the build private key"
token_mode="$(stat -c '%a' "${token_file}")"
[[ "${token_mode}" == "600" || "${token_mode}" == "400" ]] \
  || die "token secret file must have mode 0600 or 0400 (found ${token_mode})"

for command in curl jq packer git stat; do
  command -v "${command}" >/dev/null 2>&1 || die "required command not found: ${command}"
done
if [[ "${validate_only}" != "1" ]]; then
  for command in ssh scp base64; do
    command -v "${command}" >/dev/null 2>&1 || die "required command not found: ${command}"
  done
fi

read_var() {
  local name="$1"
  awk -v name="${name}" '
    $1 == name && $2 == "=" {
      value = $0
      sub(/^[^=]*=[[:space:]]*/, "", value)
      sub(/[[:space:]]*#.*/, "", value)
      gsub(/^"|"$/, "", value)
      print value
      exit
    }
  ' "${var_file}"
}

api_url="$(read_var proxmox_api_url)"
node="$(read_var proxmox_node)"
token_id="$(read_var proxmox_token_id)"
storage="$(read_var proxmox_storage_pool)"
source_template="$(read_var proxmox_source_template)"
insecure="$(read_var proxmox_insecure_skip_tls_verify)"
[[ "${api_url}" =~ ^https://[^/]+:8006/api2/json/?$ ]] || die "proxmox_api_url must be https://HOST:8006/api2/json"
[[ -n "${node}" && -n "${storage}" && -n "${source_template}" ]] || die "var file is missing node, storage, or source template"
[[ "${token_id}" =~ ^[^@[:space:]]+@[^![:space:]]+![^[:space:]]+$ ]] || die "proxmox_token_id must match user@realm!token-name"
[[ "${insecure}" == "true" || "${insecure}" == "false" ]] || die "proxmox_insecure_skip_tls_verify must be true or false"

token_secret="$(tr -d '\r\n' < "${token_file}")"
[[ -n "${token_secret}" ]] || die "token secret file is empty"
curl_config="$(mktemp)"
trap 'rm -f "${curl_config}"' EXIT
chmod 0600 "${curl_config}"
printf 'silent\nshow-error\nfail\nheader = "Authorization: PVEAPIToken=%s=%s"\n' \
  "${token_id}" "${token_secret}" > "${curl_config}"
curl_tls=()
if [[ "${insecure}" == "true" ]]; then
  curl_tls+=(--insecure)
  log "WARNING: Proxmox TLS certificate verification is disabled for this lab build"
fi
api_url="${api_url%/}"
api_get() { curl "${curl_tls[@]}" --config "${curl_config}" "${api_url}$1"; }

log "checking Proxmox API access and build resources"
api_get /version >/dev/null || die "cannot authenticate to the Proxmox API"
api_get "/nodes/${node}/status" >/dev/null || die "token cannot access node ${node}"
storage_json="$(api_get "/nodes/${node}/storage")" || die "token cannot list storage on ${node}"
jq -e --arg storage "${storage}" '.data[] | select(.storage == $storage)' <<<"${storage_json}" >/dev/null \
  || die "storage ${storage} is absent or not visible to the token"
qemu_json="$(api_get "/nodes/${node}/qemu")" || die "token cannot list VMs on ${node}"
jq -e --arg name "${source_template}" '.data[] | select(.name == $name and .template == 1)' <<<"${qemu_json}" >/dev/null \
  || die "source template not found or not visible: ${source_template}"
jq -e --argjson vmid "${vmid}" '.data[] | select(.vmid == $vmid)' <<<"${qemu_json}" >/dev/null \
  && die "output VMID ${vmid} already exists; immutable candidates require an unused VMID"

source_commit="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
template_name="flowform-golden-al2023-${source_commit:0:8}-${vmid}"
packer_args=(
  -only=proxmox-clone.amazon_linux_2023
  -var-file="${var_file}"
  -var="proxmox_vm_id=${vmid}"
  -var="proxmox_template_name=${template_name}"
  -var="source_commit=${source_commit}"
)
export PKR_VAR_proxmox_token_secret="${token_secret}"
export PKR_VAR_proxmox_ssh_private_key_file="${private_key}"
unset token_secret

cd "${PACKER_DIR}"
packer init .
packer fmt -check -recursive .
packer validate "${packer_args[@]}" .
if [[ "${validate_only}" == "1" ]]; then
  log "validation succeeded; build skipped (--validate-only)"
  exit 0
fi

packer build "${packer_args[@]}" .
remote_smoke="/var/lib/flowform/image-factory/smoke-test-template.sh"
ssh "${verify_on}" install -d -m 0700 /var/lib/flowform/image-factory
scp "${SCRIPT_DIR}/../platforms/proxmox/smoke-test-template.sh" "${verify_on}:${remote_smoke}"
smoke_output="$(ssh "${verify_on}" "${remote_smoke}" --template-vmid "${vmid}")"
printf '%s\n' "${smoke_output}"
smoke_report_b64="$(sed -n 's/^FLOWFORM_SMOKE_REPORT_B64=//p' <<<"${smoke_output}" | tail -n 1)"
[[ -n "${smoke_report_b64}" ]] || die "smoke verification did not return a tool-version report"
smoke_tool_versions="$(printf '%s' "${smoke_report_b64}" | base64 --decode)"
install -d -m 0750 "${output_dir}"
packer_version="$(packer version | head -n 1)"
packer_plugins="$(packer plugins installed 2>/dev/null || true)"
jq -n \
  --arg schema "flowform.proxmox-image-manifest/1" \
  --argjson image_contract_version 1 \
  --argjson vmid "${vmid}" \
  --arg name "${template_name}" \
  --arg source_template "${source_template}" \
  --arg source_version "${AL2023_VERSION}" \
  --arg source_sha256 "${AL2023_SHA256}" \
  --arg source_commit "${source_commit}" \
  --arg packer_version "${packer_version}" \
  --arg packer_plugins "${packer_plugins}" \
  --arg smoke_tool_versions "${smoke_tool_versions}" \
  --arg built_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{schema:$schema, image_contract_version:$image_contract_version,
    vmid:$vmid, name:$name, source_template:$source_template,
    source_image:{version:$source_version, sha256:$source_sha256},
    source_commit:$source_commit, packer_version:$packer_version,
    packer_plugins:($packer_plugins | split("\n") | map(select(length > 0))),
    guest_tool_versions:($smoke_tool_versions | split("\n") | map(select(length > 0))),
    built_at:$built_at, smoke_verified:true}' \
  > "${output_dir}/manifest.json"
chmod 0640 "${output_dir}/manifest.json"
log "built candidate ${vmid}; manifest: ${output_dir}/manifest.json"
log "candidate ${vmid} passed smoke verification and is selectable"
