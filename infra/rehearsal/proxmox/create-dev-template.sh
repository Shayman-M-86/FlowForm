#!/usr/bin/env bash
set -Eeuo pipefail

# Build the dev/jump-box template (VMID 9002) — golden 9000 PLUS operator
# conveniences (run ON the PVE host). The dev box is an out-of-scope WORKBENCH,
# not part of the topology under test: dual-homed (LAN + private net) so an
# operator can SSH in from the LAN, install things freely, and reach the private
# fake-AWS. verify.sh never asserts anything about it.
#
# Same pattern as all templates: clone 9000 → attach dev-builder.user-data →
# boot → cloud-init installs dev extras (git, yq, awslocal, ...), cleans, powers
# off → host waits for 'stopped' → template. No qm guest exec in the bake path.
#
# Idempotent: refuses if 9002 exists (use --force to rebuild).

SRC_TEMPLATE="${SRC_TEMPLATE:-9000}"
VMID="${VMID:-9002}"
NAME="flowform-rehearsal-dev-golden"
DISK_STORAGE="${DISK_STORAGE:-ZFS-RAIDZ}"
SNIPPET_STORAGE="${SNIPPET_STORAGE:-local}"
LAN_BRIDGE="${LAN_BRIDGE:-vmbr0}"          # builder needs internet to install extras
BUILD_TIMEOUT="${BUILD_TIMEOUT:-900}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
USER_DATA_SRC="${USER_DATA_SRC:-${SCRIPT_DIR}/cloud-init/dev-builder.user-data.yaml}"
SNIPPET_NAME="flowform-dev-builder.yaml"
# shellcheck source=lib/template-build.sh
source "${SCRIPT_DIR}/lib/template-build.sh"

FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

log() { printf '[create-dev-template] %s\n' "$*"; }
die() { printf '[create-dev-template] ERROR: %s\n' "$*" >&2; exit 1; }

qm status "${SRC_TEMPLATE}" >/dev/null 2>&1 || die "source template ${SRC_TEMPLATE} not found — run create-template.sh first"

if qm status "${VMID}" >/dev/null 2>&1; then
  if [[ "${FORCE}" == "1" ]]; then
    log "VMID ${VMID} exists — destroying (--force)"
    qm stop "${VMID}" >/dev/null 2>&1 || true
    qm destroy "${VMID}" --purge
  else
    die "VMID ${VMID} already exists. Re-run with --force to rebuild."
  fi
fi

# --- 1. clone + attach the builder user-data ------------------------------
log "cloning ${SRC_TEMPLATE} → ${VMID} (${NAME})"
qm clone "${SRC_TEMPLATE}" "${VMID}" --name "${NAME}" --full --storage "${DISK_STORAGE}"

CICUSTOM="$(tb_install_snippet "${USER_DATA_SRC}" "${SNIPPET_NAME}" "${SNIPPET_STORAGE}")" \
  || die "could not install builder user-data"
log "installed builder user-data → ${CICUSTOM}"
qm set "${VMID}" --net0 "virtio,bridge=${LAN_BRIDGE}" --ipconfig0 "ip=dhcp" >/dev/null
qm set "${VMID}" --cicustom "user=${CICUSTOM}" >/dev/null

# --- 2. boot; cloud-init installs extras, cleans, powers off --------------
log "starting builder — cloud-init installs dev extras, cleans, then powers off"
qm start "${VMID}"
tb_wait_stopped "${VMID}" "${BUILD_TIMEOUT}" "create-dev-template" || die "build failed"

# --- 3. finalize (dev box gets NICs fresh from create-vms.sh) -------------
qm set "${VMID}" --delete net0 >/dev/null 2>&1 || true
tb_finalize_template "${VMID}" "create-dev-template"
log "done — dev-box template ${VMID} ready. create-vms.sh clones 240 from it (WITH_DEV_BOX=1)."
