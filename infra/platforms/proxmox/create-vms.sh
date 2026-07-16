#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: create-vms.sh --image-manifest FILE [--with-dev] [--force]

Run on Proxmox VE. Clones and configures the rehearsal topology from a verified
immutable image manifest. VMs remain stopped; activate.sh owns every first boot.

Options:
  --image-manifest FILE  Required verified FlowForm image manifest
  --with-dev             Include optional developer workbench VM 240
  --force                Recreate matching rehearsal VMIDs if they exist
  --help                 Show this help
USAGE
}

log() { printf '[create-vms] %s\n' "$*"; }
die() { printf '[create-vms] ERROR: %s\n' "$*" >&2; exit 1; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd -- "${SCRIPT_DIR}/../../.." && pwd)}"
STATE_DIR="${FLOWFORM_REHEARSAL_STATE_DIR:-/var/lib/flowform/rehearsal}"
STATE_FILE="${STATE_DIR}/state.json"
# shellcheck source=lib/cloud-init-snippets.sh
. "${SCRIPT_DIR}/lib/cloud-init-snippets.sh"

manifest=""
with_dev=0
force=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --image-manifest) manifest="${2:-}"; shift 2 ;;
    --with-dev) with_dev=1; shift ;;
    --force) force=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ "${EUID}" -eq 0 || "${FLOWFORM_TEST_MODE:-0}" == "1" ]] || die "run as root on the Proxmox host"
[[ -f "${manifest}" ]] || die "--image-manifest does not exist: ${manifest}"
for command in jq qm ip ssh-keygen; do
  command -v "${command}" >/dev/null 2>&1 || die "required command not found: ${command}"
done
jq -e '.schema == "flowform.proxmox-image-manifest/1" and .smoke_verified == true' "${manifest}" >/dev/null \
  || die "image manifest is invalid or has not passed smoke verification"
template_vmid="$(jq -er '.vmid' "${manifest}")"
template_name="$(jq -er '.name' "${manifest}")"
qm status "${template_vmid}" >/dev/null 2>&1 || die "template ${template_vmid} not found"
qm config "${template_vmid}" | grep -q '^template: 1$' || die "VMID ${template_vmid} is not a template"

disk_storage="${DISK_STORAGE:-ZFS-RAIDZ}"
private_bridge="${PRIV_BRIDGE:-vmbr10}"
lan_bridge="${LAN_BRIDGE:-vmbr0}"
private_cidr="${PRIV_CIDR:-24}"
dev_lan_ip="${DEV_LAN_IP:-192.168.68.100}"
dev_lan_gw="${DEV_LAN_GW:-192.168.68.1}"
dev_lan_cidr="${DEV_LAN_CIDR:-24}"
ip -br link show "${private_bridge}" >/dev/null 2>&1 || die "${private_bridge} missing; run setup-host.sh first"

install -d -m 0700 "${STATE_DIR}/ssh"
orchestration_key="${STATE_DIR}/ssh/id_ed25519"
if [[ ! -s "${orchestration_key}" ]]; then
  ssh-keygen -q -t ed25519 -N '' -C flowform-rehearsal-orchestrator -f "${orchestration_key}"
fi
chmod 0600 "${orchestration_key}"
chmod 0644 "${orchestration_key}.pub"

generated_dir="${REPO_ROOT}/infra/.generated/cloud-init"
OUTPUT_DIR="${generated_dir}" REPO_ROOT="${REPO_ROOT}" \
  "${REPO_ROOT}/infra/runtime/cloud-init/render-user-data.sh"

APP_USERDATA_REF="$(proxmox_install_snippet "${generated_dir}/app.user-data.rendered.yaml" flowform-app.user-data.yaml)"
PROXY_USERDATA_REF="$(proxmox_install_snippet "${generated_dir}/proxy.user-data.rendered.yaml" flowform-proxy.user-data.yaml)"
FIXTURES_USERDATA_REF="$(proxmox_install_snippet "${generated_dir}/localstack.user-data.rendered.yaml" flowform-fixtures.user-data.yaml)"
DEV_USERDATA_REF=""
if [[ "${with_dev}" == "1" ]]; then
  DEV_USERDATA_REF="$(proxmox_install_snippet "${generated_dir}/dev.user-data.rendered.yaml" flowform-dev.user-data.yaml)"
fi

clone_or_reuse() {
  local vmid="$1" expected_name="$2"
  if qm status "${vmid}" >/dev/null 2>&1; then
    if [[ "${force}" == "1" ]]; then
      log "destroying existing rehearsal VM ${vmid} (--force)"
      qm stop "${vmid}" >/dev/null 2>&1 || true
      qm destroy "${vmid}" --purge
    else
      actual_name="$(qm config "${vmid}" | awk -F': ' '$1 == "name" {print $2}')"
      [[ "${actual_name}" == "${expected_name}" ]] \
        || die "VMID ${vmid} belongs to ${actual_name:-an unknown VM}; refusing to reuse it"
      log "reusing stopped rehearsal VM ${vmid} (${expected_name})"
      qm stop "${vmid}" >/dev/null 2>&1 || true
      return
    fi
  fi
  log "cloning verified template ${template_vmid} -> ${vmid} (${expected_name})"
  qm clone "${template_vmid}" "${vmid}" --name "${expected_name}" --full --storage "${disk_storage}"
}

configure_common() {
  local vmid="$1" userdata_ref="$2"
  qm set "${vmid}" \
    --cicustom "user=${userdata_ref}" \
    --ciuser flowform \
    --sshkeys "${orchestration_key}.pub"
}

clone_or_reuse 210 flowform-rehearsal-proxy
qm set 210 \
  --net0 "virtio,bridge=${lan_bridge}" \
  --net1 "virtio,bridge=${private_bridge}" \
  --ipconfig0 ip=dhcp \
  --ipconfig1 "ip=10.10.10.10/${private_cidr}"
configure_common 210 "${PROXY_USERDATA_REF}"

clone_or_reuse 220 flowform-rehearsal-app
qm set 220 \
  --net0 "virtio,bridge=${private_bridge}" \
  --ipconfig0 "ip=10.10.10.20/${private_cidr}"
configure_common 220 "${APP_USERDATA_REF}"

clone_or_reuse 230 flowform-rehearsal-fixtures
qm set 230 \
  --net0 "virtio,bridge=${private_bridge}" \
  --ipconfig0 "ip=10.10.10.30/${private_cidr}"
configure_common 230 "${FIXTURES_USERDATA_REF}"

vmids=(210 220 230)
if [[ "${with_dev}" == "1" ]]; then
  clone_or_reuse 240 flowform-rehearsal-dev
  qm set 240 \
    --net0 "virtio,bridge=${lan_bridge}" \
    --net1 "virtio,bridge=${private_bridge}" \
    --ipconfig0 "ip=${dev_lan_ip}/${dev_lan_cidr},gw=${dev_lan_gw}" \
    --ipconfig1 "ip=10.10.10.40/${private_cidr}"
  configure_common 240 "${DEV_USERDATA_REF}"
  vmids+=(240)
fi

install -d -m 0700 "${STATE_DIR}"
install -m 0600 "${manifest}" "${STATE_DIR}/image-manifest.json"
vmids_json="$(printf '%s\n' "${vmids[@]}" | jq -s 'map(tonumber)')"
jq -n \
  --arg schema flowform.rehearsal-state/1 \
  --argjson template_vmid "${template_vmid}" \
  --arg template_name "${template_name}" \
  --argjson vmids "${vmids_json}" \
  --argjson with_dev "$( [[ "${with_dev}" == "1" ]] && echo true || echo false )" \
  --arg created_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{schema:$schema, template:{vmid:$template_vmid,name:$template_name},
    vmids:$vmids, with_dev:$with_dev, status:"created", created_at:$created_at}' \
  > "${STATE_FILE}"
chmod 0600 "${STATE_FILE}"

log "topology created from ${template_name}; all VMs are stopped"
log "next: infra/environments/rehearsal/activate.sh --artifact-manifest FILE"
