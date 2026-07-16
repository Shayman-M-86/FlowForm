#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: import-source-image.sh --source-vmid ID --image FILE --ssh-public-key FILE [options]

Run on a Proxmox VE host. Imports a verified Amazon Linux qcow2 as the minimal
source template that Packer clones and customizes.

Options:
  --source-vmid ID       Required source-template VMID
  --image FILE           Required local qcow2 path
  --ssh-public-key FILE  Required temporary Packer build public key
  --name NAME            Source-template name
  --storage NAME         Proxmox storage (default: ZFS-RAIDZ)
  --bridge NAME          Build network bridge (default: vmbr0)
  --replace              Destroy an existing VM/template with the same VMID
  --help                 Show this help
USAGE
}

log() { printf '[import-source-image] %s\n' "$*"; }
die() { printf '[import-source-image] ERROR: %s\n' "$*" >&2; exit 1; }

source_vmid=""
image=""
ssh_public_key=""
name="amazon-linux-2023-kvm-base"
storage="${PROXMOX_STORAGE:-ZFS-RAIDZ}"
bridge="${PROXMOX_BUILD_BRIDGE:-vmbr0}"
replace=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source-vmid) source_vmid="${2:-}"; shift 2 ;;
    --image) image="${2:-}"; shift 2 ;;
    --ssh-public-key) ssh_public_key="${2:-}"; shift 2 ;;
    --name) name="${2:-}"; shift 2 ;;
    --storage) storage="${2:-}"; shift 2 ;;
    --bridge) bridge="${2:-}"; shift 2 ;;
    --replace) replace=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ "${EUID}" -eq 0 ]] || die "run as root on the Proxmox host"
[[ "${source_vmid}" =~ ^[1-9][0-9]{2,8}$ ]] || die "--source-vmid must be a valid numeric VMID"
[[ -f "${image}" ]] || die "image not found: ${image}"
[[ -s "${ssh_public_key}" ]] || die "SSH public key not found or empty: ${ssh_public_key}"
command -v qm >/dev/null 2>&1 || die "qm not found; run this on a Proxmox VE host"
pvesm status --storage "${storage}" >/dev/null 2>&1 || die "storage not available: ${storage}"
ip link show "${bridge}" >/dev/null 2>&1 || die "bridge not found: ${bridge}"

if qm status "${source_vmid}" >/dev/null 2>&1; then
  [[ "${replace}" == "1" ]] || die "VMID ${source_vmid} already exists; choose another ID or pass --replace"
  log "destroying existing VMID ${source_vmid} (--replace)"
  qm stop "${source_vmid}" >/dev/null 2>&1 || true
  qm destroy "${source_vmid}" --purge
fi

log "creating source VM ${source_vmid} (${name})"
qm create "${source_vmid}" \
  --name "${name}" \
  --description "FlowForm pinned Amazon Linux source; Packer input only" \
  --cores 2 --memory 2048 \
  --net0 "virtio,bridge=${bridge}" \
  --scsihw virtio-scsi-single \
  --ostype l26 \
  --agent enabled=1 \
  --serial0 socket --vga serial0

log "importing ${image} into ${storage}"
qm importdisk "${source_vmid}" "${image}" "${storage}"
imported_volume="$(qm config "${source_vmid}" | awk -F': ' '/^unused[0-9]+:/{print $2; exit}')"
[[ -n "${imported_volume}" ]] || die "could not locate imported disk in qm config ${source_vmid}"

qm set "${source_vmid}" \
  --scsi0 "${imported_volume},discard=on,ssd=1" \
  --ide2 "${storage}:cloudinit" \
  --boot "order=scsi0" \
  --ciuser ec2-user \
  --sshkeys "${ssh_public_key}" \
  --ipconfig0 ip=dhcp
qm template "${source_vmid}"
log "source template ${source_vmid} (${name}) is ready"
