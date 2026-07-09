#!/usr/bin/env bash
set -Eeuo pipefail

# Build the ls-vm template (VMID 9001) — golden 9000 PLUS the LocalStack image
# pre-pulled (run ON the PVE host). LocalStack is fake-AWS scaffolding, baked into
# the image it runs on rather than delivered via the private registry (that path
# is reserved for the real backend image). The app VM (from 9000) never carries it.
#
# Same pattern as all templates: clone 9000 → attach localstack-builder.user-data
# → boot → cloud-init pulls the image, cleans, powers off → host waits for
# 'stopped' → template. No qm guest exec in the bake path.
#
# Idempotent: refuses if 9001 exists (use --force to rebuild).

SRC_TEMPLATE="${SRC_TEMPLATE:-9000}"
VMID="${VMID:-9001}"
NAME="flowform-rehearsal-ls-golden"
DISK_STORAGE="${DISK_STORAGE:-ZFS-RAIDZ}"
SNIPPET_STORAGE="${SNIPPET_STORAGE:-local}"
LAN_BRIDGE="${LAN_BRIDGE:-vmbr0}"          # builder needs internet to pull the image
BUILD_TIMEOUT="${BUILD_TIMEOUT:-900}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
USER_DATA_SRC="${USER_DATA_SRC:-${SCRIPT_DIR}/cloud-init/localstack-builder.user-data.yaml}"
SNIPPET_NAME="flowform-localstack-builder.yaml"
# shellcheck source=lib/template-build.sh
source "${SCRIPT_DIR}/lib/template-build.sh"

FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

log() { printf '[create-ls-template] %s\n' "$*"; }
die() { printf '[create-ls-template] ERROR: %s\n' "$*" >&2; exit 1; }

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

# --- 2. boot; cloud-init pulls the image, cleans, powers off --------------
log "starting builder — cloud-init pulls localstack, cleans, then powers off"
qm start "${VMID}"
tb_wait_stopped "${VMID}" "${BUILD_TIMEOUT}" "create-ls-template" || die "build failed"

# --- 3. strip the temp internet NIC + finalize ----------------------------
# The ls-vm runs private-only; drop the builder's LAN NIC before templating.
qm set "${VMID}" --delete net0 >/dev/null 2>&1 || true
tb_finalize_template "${VMID}" "create-ls-template"
log "done — ls-vm template ${VMID} ready (localstack pre-pulled). create-vms.sh clones 230 from it."
