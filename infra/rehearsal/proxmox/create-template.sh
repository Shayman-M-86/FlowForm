#!/usr/bin/env bash
set -Eeuo pipefail

# Build the FlowForm rehearsal GOLDEN TEMPLATE on the Proxmox host (run ON PVE).
#
# This template is the local mirror of the future production golden AMI. It bakes
# ONLY host-level dependencies — Docker, the Compose plugin, guest agent, base
# tools, and hardening — into an Ubuntu 24.04 (noble) cloud image using
# virt-customize (offline; no VM boot, no temporary internet egress). App code,
# secrets, and env config are deliberately NOT baked; they arrive at runtime.
#
# Layering this enforces (see project golden-image decision):
#   template  = host deps        (this script)
#   docker img= the app          (built elsewhere, pulled at runtime)
#   runtime   = secrets + config (bootstrap-app.sh: tmpfs secrets, backend.env)
#
# Idempotent: if VMID 9000 already exists it refuses (use --force to rebuild).
# The finished VM is converted to a template; clone it with create-vms.sh.
#
# Does NOT touch vmbr0, vmbr10, or any existing VM.

VMID="${VMID:-9000}"
NAME="flowform-rehearsal-golden"
DISK_STORAGE="${DISK_STORAGE:-ZFS-RAIDZ}"    # where the template disk lives
SNIPPET_STORAGE="${SNIPPET_STORAGE:-local}"  # must have 'snippets' content (setup-host.sh)
IMG_URL="https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
IMG_DIR="/var/lib/vz/template/iso"
IMG_FILE="${IMG_DIR}/noble-server-cloudimg-amd64.img"
BRIDGE="${BRIDGE:-vmbr0}"                     # template's default NIC (clones override)

FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

log() { printf '[create-template] %s\n' "$*"; }
die() { printf '[create-template] ERROR: %s\n' "$*" >&2; exit 1; }

# --- 0. preflight ---------------------------------------------------------
command -v qm >/dev/null            || die "qm not found — run this on the PVE host"
command -v virt-customize >/dev/null || {
  log "virt-customize missing — installing libguestfs-tools"
  apt-get update -qq && apt-get install -y libguestfs-tools >/dev/null
}
command -v qemu-img >/dev/null      || die "qemu-img not found"

if qm status "${VMID}" >/dev/null 2>&1; then
  if [[ "${FORCE}" == "1" ]]; then
    log "VMID ${VMID} exists — destroying (--force)"
    qm destroy "${VMID}" --purge
  else
    die "VMID ${VMID} already exists. Re-run with --force to rebuild, or pick another VMID=."
  fi
fi

# --- 1. fetch the cloud image (once) --------------------------------------
install -d -m 0755 "${IMG_DIR}"
if [[ -f "${IMG_FILE}" ]]; then
  log "cloud image already present: ${IMG_FILE}"
else
  log "downloading Ubuntu 24.04 cloud image"
  wget -q --show-progress -O "${IMG_FILE}.tmp" "${IMG_URL}"
  mv "${IMG_FILE}.tmp" "${IMG_FILE}"
fi

# Work on a COPY so the pristine download can be reused on a rebuild.
WORK_IMG="${IMG_DIR}/${NAME}-${VMID}.img"
log "copying image to work file: ${WORK_IMG}"
cp -f "${IMG_FILE}" "${WORK_IMG}"

# Cloud images ship small (~2.2G virtual). Grow before customizing so the baked
# packages fit and clones have headroom.
log "resizing work image to 10G"
qemu-img resize "${WORK_IMG}" 10G >/dev/null

# --- 2. bake host deps offline (virt-customize) ---------------------------
# One --run-command block so apt state stays consistent. Installs Docker from
# Docker's official repo (Compose plugin included), plus base tools + guest
# agent. Enables services so they're active on first boot. Cleans apt caches so
# the template stays lean. NO app, NO secrets.
log "baking host dependencies into image (offline)"
virt-customize -a "${WORK_IMG}" \
  --run-command 'export DEBIAN_FRONTEND=noninteractive' \
  --run-command 'apt-get update' \
  --run-command 'apt-get install -y ca-certificates curl jq unzip gnupg qemu-guest-agent nftables' \
  --run-command 'install -m 0755 -d /etc/apt/keyrings' \
  --run-command 'curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && chmod a+r /etc/apt/keyrings/docker.asc' \
  --run-command 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" > /etc/apt/sources.list.d/docker.list' \
  --run-command 'apt-get update' \
  --run-command 'apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin' \
  --run-command 'systemctl enable docker qemu-guest-agent' \
  --run-command 'install -d -m 0755 /opt/flowform' \
  --run-command 'apt-get clean && rm -rf /var/lib/apt/lists/*' \
  --run-command 'truncate -s 0 /etc/machine-id'  # regenerate per-clone

# --- 3. create the VM shell + attach the disk -----------------------------
log "creating VM ${VMID} (${NAME})"
qm create "${VMID}" \
  --name "${NAME}" \
  --memory 2048 --cores 2 \
  --net0 "virtio,bridge=${BRIDGE}" \
  --scsihw virtio-scsi-single \
  --ostype l26 \
  --agent enabled=1 \
  --serial0 socket --vga serial0        # cloud images expect a serial console

log "importing baked disk to ${DISK_STORAGE}"
qm importdisk "${VMID}" "${WORK_IMG}" "${DISK_STORAGE}" >/dev/null
qm set "${VMID}" --scsi0 "${DISK_STORAGE}:vm-${VMID}-disk-0" >/dev/null

# cloud-init drive (create-vms.sh fills user/network via --cicustom / --ipconfig)
qm set "${VMID}" --ide2 "${DISK_STORAGE}:cloudinit" >/dev/null
qm set "${VMID}" --boot order=scsi0 >/dev/null

# --- 4. convert to template -----------------------------------------------
log "converting VM ${VMID} to a template"
qm template "${VMID}"

rm -f "${WORK_IMG}"
log "done — template ${VMID} (${NAME}) ready. Clone it with create-vms.sh."
