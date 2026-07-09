#!/usr/bin/env bash
set -Eeuo pipefail

# Build the FlowForm rehearsal GOLDEN TEMPLATE on the Proxmox host (run ON PVE).
#
# Local mirror of the future production golden AMI. Bakes host-level dependencies
# ONLY — Docker + Compose plugin, AWS CLI v2, qemu-guest-agent, base tools. App
# code, secrets, and env config are NOT baked; they arrive at runtime.
#
# Method (fully declarative, no agent/SSH/offline mutation):
#   1. host: create builder VM from the Ubuntu cloud image, resize disk via qm.
#   2. cloud-init (golden-builder.user-data.yaml): self-installs the base,
#      cleans itself, then powers the VM off.
#   3. host: wait for the VM to reach 'stopped' (the done-signal), convert to a
#      template. No guest access needed — power state is the only signal.
#
# The bare cloud image has no qemu-guest-agent, so we CANNOT drive the golden
# build via `qm guest exec` (chicken-and-egg). cloud-init does the whole install
# instead. Clones of this template DO have the agent, so create-localstack/dev
# templates can use guest-exec.
#
# Idempotent: refuses if VMID 9000 exists (use --force). Reproducible from
# scratch on a fresh Proxmox host. Does NOT touch vmbr0/vmbr10/other VMs.

VMID="${VMID:-9000}"
NAME="flowform-rehearsal-golden"
DISK_STORAGE="${DISK_STORAGE:-ZFS-RAIDZ}"
DISK_SIZE="${DISK_SIZE:-16G}"
SNIPPET_STORAGE="${SNIPPET_STORAGE:-local}"   # needs 'snippets' content (setup-host.sh)
IMG_URL="https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
IMG_DIR="/var/lib/vz/template/iso"
IMG_FILE="${IMG_DIR}/noble-server-cloudimg-amd64.img"
LAN_BRIDGE="${LAN_BRIDGE:-vmbr0}"
BUILD_TIMEOUT="${BUILD_TIMEOUT:-900}"          # seconds to wait for cloud-init → poweroff

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
USER_DATA_SRC="${USER_DATA_SRC:-${SCRIPT_DIR}/cloud-init/golden-builder.user-data.yaml}"
SNIPPET_NAME="flowform-golden-builder.yaml"
# shellcheck source=lib/template-build.sh
source "${SCRIPT_DIR}/lib/template-build.sh"

FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

log() { printf '[create-template] %s\n' "$*"; }
die() { printf '[create-template] ERROR: %s\n' "$*" >&2; exit 1; }

# --- 0. preflight ---------------------------------------------------------
command -v qm >/dev/null       || die "qm not found — run this on the PVE host"
command -v qemu-img >/dev/null || die "qemu-img not found"
[[ -f "${USER_DATA_SRC}" ]]    || die "user-data snippet missing: ${USER_DATA_SRC}"
pvesm status --content snippets 2>/dev/null | grep -q "^${SNIPPET_STORAGE}\b" \
  || die "storage '${SNIPPET_STORAGE}' has no 'snippets' content — run setup-host.sh"

if qm status "${VMID}" >/dev/null 2>&1; then
  if [[ "${FORCE}" == "1" ]]; then
    log "VMID ${VMID} exists — destroying (--force)"
    qm stop "${VMID}" >/dev/null 2>&1 || true
    qm destroy "${VMID}" --purge
  else
    die "VMID ${VMID} already exists. Re-run with --force to rebuild."
  fi
fi

# --- 1. fetch the cloud image (once) --------------------------------------
install -d -m 0755 "${IMG_DIR}"
if [[ -f "${IMG_FILE}" ]]; then
  log "cloud image already present: ${IMG_FILE}"
else
  log "downloading Ubuntu 24.04 cloud image"
  wget -q -O "${IMG_FILE}.tmp" "${IMG_URL}"
  mv "${IMG_FILE}.tmp" "${IMG_FILE}"
fi

# --- 2. install the builder user-data into snippets storage ---------------
CICUSTOM="$(tb_install_snippet "${USER_DATA_SRC}" "${SNIPPET_NAME}" "${SNIPPET_STORAGE}")" \
  || die "could not install builder user-data"
log "installed builder user-data → ${CICUSTOM}"

# --- 3. create the builder VM + disk (resize THROUGH Proxmox) -------------
log "creating builder VM ${VMID} (${NAME})"
qm create "${VMID}" \
  --name "${NAME}" \
  --memory 2048 --cores 2 \
  --net0 "virtio,bridge=${LAN_BRIDGE}" \
  --scsihw virtio-scsi-single \
  --ostype l26 \
  --agent enabled=1 \
  --serial0 socket --vga serial0

log "importing cloud image to ${DISK_STORAGE}"
qm importdisk "${VMID}" "${IMG_FILE}" "${DISK_STORAGE}" >/dev/null
qm set "${VMID}" --scsi0 "${DISK_STORAGE}:vm-${VMID}-disk-0" >/dev/null
qm set "${VMID}" --ide2 "${DISK_STORAGE}:cloudinit" >/dev/null
qm set "${VMID}" --boot order=scsi0 >/dev/null

log "resizing disk to ${DISK_SIZE} (growpart expands root at first boot)"
qm disk resize "${VMID}" scsi0 "${DISK_SIZE}"

# Attach our custom user-data; DHCP for internet during the build.
qm set "${VMID}" --ipconfig0 "ip=dhcp" >/dev/null
qm set "${VMID}" --cicustom "user=${CICUSTOM}" >/dev/null

# --- 4. boot; cloud-init installs + cleans + powers off -------------------
log "starting builder — cloud-init will install the base, clean, then power off"
qm start "${VMID}"
tb_wait_stopped "${VMID}" "${BUILD_TIMEOUT}" "create-template" || die "build failed"

# --- 5. finalize: detach build-time cloud-init, convert to template -------
tb_finalize_template "${VMID}" "create-template"
log "done — template ${VMID} (${NAME}) ready. Clone it with create-vms.sh."
