#!/usr/bin/env bash
set -Eeuo pipefail

# Clone the golden template (9000) into the three rehearsal VMs and start them
# (run ON the PVE host). Network wiring here IS the rehearsal's point:
#
#   proxy-vm (210)  NIC0 vmbr0 (LAN) + NIC1 vmbr10   10.10.10.10  — HAS internet
#   app-vm   (220)  NIC0 vmbr10 ONLY, NO gateway     10.10.10.20  — NO internet
#   ls-vm    (230)  NIC0 vmbr10 ONLY                 10.10.10.30  — private only
#
# The app box's isolation is STRUCTURAL: its only NIC is on vmbr10 (which has no
# uplink and no gateway) and its ipconfig sets no gateway — so it cannot route
# off the private net. That's what makes "forced egress via Squid" honest.
#
# Static IPs via cloud-init ipconfig (no DHCP on the private net). Idempotent:
# existing VMIDs are skipped unless --force (destroy + reclone).
#
# The app box (220) boots with cloud-init user-data (--cicustom) that trusts the
# rehearsal CA, resolves the *.localstack.test SNI names to the ls-vm, and runs
# bootstrap-app.sh. That user-data is RENDERED from the real repo files by
# infra/runtime/cloud-init/render-user-data.sh (single source of truth) — this script renders
# it and installs it as a PVE snippet before cloning 220.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/cloud-init-snippets.sh
. "${SCRIPT_DIR}/lib/cloud-init-snippets.sh"

TEMPLATE_VMID="${TEMPLATE_VMID:-9000}"        # golden base → proxy + app
LS_TEMPLATE_VMID="${LS_TEMPLATE_VMID:-${TEMPLATE_VMID}}"  # default: clone golden; LocalStack fixtures are runtime-managed
DEV_TEMPLATE_VMID="${DEV_TEMPLATE_VMID:-${TEMPLATE_VMID}}" # default: clone golden; dev extras are runtime-managed
DISK_STORAGE="${DISK_STORAGE:-ZFS-RAIDZ}"

# The dev box is an OUT-OF-SCOPE operator workbench, off by default so clean
# isolation runs aren't influenced by it. Set WITH_DEV_BOX=1 to create/start it.
WITH_DEV_BOX="${WITH_DEV_BOX:-0}"
# Static LAN address for the dev box so `ssh flowform@<ip>` never drifts. Must be
# OUTSIDE the router's DHCP pool. gw = the LAN gateway (same one DHCP hands out).
DEV_LAN_IP="${DEV_LAN_IP:-192.168.68.100}"
DEV_LAN_GW="${DEV_LAN_GW:-192.168.68.1}"
DEV_LAN_CIDR="${DEV_LAN_CIDR:-24}"
PRIV_BRIDGE="vmbr10"
LAN_BRIDGE="vmbr0"
PRIV_CIDR="24"

# VMID : name : ipconfig0 spec  (gateway ONLY where a route off-net is intended)
#   proxy: LAN NIC (net0, dhcp on vmbr0) + private NIC (net1, static, no gw)
#   app  : private NIC only, static, NO gateway  → structurally offline
#   ls   : private NIC only, static, NO gateway
#   dev  : LAN NIC (net0, dhcp on vmbr0, DEFAULT ROUTE) + private NIC (net1) — workbench
PROXY_VMID=210
APP_VMID=220
LS_VMID=230
DEV_VMID=240

FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

log() { printf '[create-vms] %s\n' "$*"; }
die() { printf '[create-vms] ERROR: %s\n' "$*" >&2; exit 1; }

qm status "${TEMPLATE_VMID}" >/dev/null 2>&1 || die "template ${TEMPLATE_VMID} not found — build it with Packer first"
qm status "${LS_TEMPLATE_VMID}" >/dev/null 2>&1 || die "ls template ${LS_TEMPLATE_VMID} not found — build the Packer golden template first"
ip -br link show "${PRIV_BRIDGE}" >/dev/null 2>&1 || die "${PRIV_BRIDGE} missing — run setup-host.sh first"
if [[ "${WITH_DEV_BOX}" == "1" ]]; then
  qm status "${DEV_TEMPLATE_VMID}" >/dev/null 2>&1 || die "dev template ${DEV_TEMPLATE_VMID} not found — build the Packer golden template first"
fi

# Render the app + proxy cloud-init from the real repo files and install them as
# PVE snippets. `create-vms.sh` runs on the PVE host from a synced copy, so the
# shared runtime/cloud-init files (templates + render script) are here; the renderer
# script reaches the repo sources via REPO_ROOT (sync from the repo root — see
# README — or export REPO_ROOT).
APP_USERDATA_REF=""
PROXY_USERDATA_REF=""
LOCALSTACK_USERDATA_REF=""
render_userdata() {
  local ci_dir="$(cd -- "${SCRIPT_DIR}/../../runtime/cloud-init" && pwd)"
  local renderer="${ci_dir}/render-user-data.sh"
  [[ -x "${renderer}" ]] || die "missing ${renderer}"
  log "rendering app + proxy cloud-init from repo sources"
  "${renderer}" || die "render-user-data.sh failed"
  APP_USERDATA_REF="$(proxmox_install_snippet "${ci_dir}/app.user-data.rendered.yaml" flowform-app.user-data.yaml)" \
    || die "installing app user-data snippet failed (run setup-host.sh?)"
  PROXY_USERDATA_REF="$(proxmox_install_snippet "${ci_dir}/proxy.user-data.rendered.yaml" flowform-proxy.user-data.yaml)" \
    || die "installing proxy user-data snippet failed (run setup-host.sh?)"
  log "app   user-data snippet: ${APP_USERDATA_REF}"
  LOCALSTACK_USERDATA_REF="$(proxmox_install_snippet "${ci_dir}/localstack.user-data.rendered.yaml" flowform-localstack.user-data.yaml)" \
    || die "installing localstack user-data snippet failed (run setup-host.sh?)"
  log "proxy user-data snippet: ${PROXY_USERDATA_REF}"
  log "localstack user-data snippet: ${LOCALSTACK_USERDATA_REF}"
}
render_userdata

# Inject the host's SSH key(s) into every clone so we can log in as 'flowform'.
# (create-template baked no keys; cloud-init sets them per-clone.)
SSHKEYS_ARGS=()
if [[ -s /root/.ssh/authorized_keys ]]; then
  SSHKEYS_ARGS=(--sshkeys /root/.ssh/authorized_keys)
else
  log "WARN: /root/.ssh/authorized_keys absent — VMs will have no SSH key (password only)"
fi

# clone_vm <vmid> <name> <template_vmid>
clone_vm() {
  local vmid="$1" name="$2" template="$3"
  if qm status "${vmid}" >/dev/null 2>&1; then
    if [[ "${FORCE}" == "1" ]]; then
      log "${vmid} exists — destroying (--force)"
      qm stop "${vmid}" >/dev/null 2>&1 || true
      qm destroy "${vmid}" --purge
    else
      log "${vmid} (${name}) already exists — skipping (use --force to reclone)"
      return 1
    fi
  fi
  log "cloning ${template} → ${vmid} (${name})"
  qm clone "${template}" "${vmid}" --name "${name}" --full --storage "${DISK_STORAGE}"
  return 0
}

# --- proxy-vm (210): LAN + private, the ONLY box with an internet route ---
# Boots the rendered proxy user-data (--cicustom): trust CA, resolve the fake-AWS
# SNI names, bring up the prod proxy stack (Caddy tls-internal +
# Squid rehearsal allow-list) via bootstrap-proxy.sh.
if clone_vm "${PROXY_VMID}" "flowform-rehearsal-proxy" "${TEMPLATE_VMID}"; then
  qm set "${PROXY_VMID}" \
    --net0 "virtio,bridge=${LAN_BRIDGE}" \
    --net1 "virtio,bridge=${PRIV_BRIDGE}" \
    --ipconfig0 "ip=dhcp" \
    --ipconfig1 "ip=10.10.10.10/${PRIV_CIDR}" \
    --cicustom "user=${PROXY_USERDATA_REF}" \
    --ciuser flowform --cipassword "rehearsal" \
    "${SSHKEYS_ARGS[@]}"
  qm start "${PROXY_VMID}"
fi

# --- app-vm (220): private NIC ONLY, NO gateway → structurally offline ----
# Boots the rendered app user-data (--cicustom): trust rehearsal CA, resolve the
# *.localstack.test SNI names to the ls-vm, run bootstrap-app.sh. bootstrap-app.sh
# needs the proxy (210) + ls-vm (230) up to reach fake-AWS through Squid → shim,
# so its egress/AWS steps only fully succeed once those are running and seeded.
if clone_vm "${APP_VMID}" "flowform-rehearsal-app" "${TEMPLATE_VMID}"; then
  qm set "${APP_VMID}" \
    --net0 "virtio,bridge=${PRIV_BRIDGE}" \
    --ipconfig0 "ip=10.10.10.20/${PRIV_CIDR}" \
    --cicustom "user=${APP_USERDATA_REF}" \
    --ciuser flowform --cipassword "rehearsal" \
    "${SSHKEYS_ARGS[@]}"
  qm start "${APP_VMID}"
fi

# --- ls-vm (230): private NIC only (LocalStack lives here) ----------------
if clone_vm "${LS_VMID}" "flowform-rehearsal-localstack" "${LS_TEMPLATE_VMID}"; then
  qm set "${LS_VMID}" \
    --net0 "virtio,bridge=${PRIV_BRIDGE}" \
    --ipconfig0 "ip=10.10.10.30/${PRIV_CIDR}" \
    --cicustom "user=${LOCALSTACK_USERDATA_REF}" \
    --ciuser flowform --cipassword "rehearsal" \
    "${SSHKEYS_ARGS[@]}"
  qm start "${LS_VMID}"
fi

# --- dev-vm (240): OUT-OF-SCOPE workbench, only when WITH_DEV_BOX=1 --------
# Dual-homed: net0 vmbr0 (DHCP, DEFAULT ROUTE → full internet + SSH from LAN),
# net1 vmbr10 (10.10.10.40 → reaches LocalStack/app/proxy). NOT measured by
# verify.sh; toggle off (qm stop 240) for clean isolation runs.
if [[ "${WITH_DEV_BOX}" == "1" ]]; then
  if clone_vm "${DEV_VMID}" "flowform-rehearsal-dev" "${DEV_TEMPLATE_VMID}"; then
    qm set "${DEV_VMID}" \
      --net0 "virtio,bridge=${LAN_BRIDGE}" \
      --net1 "virtio,bridge=${PRIV_BRIDGE}" \
      --ipconfig0 "ip=${DEV_LAN_IP}/${DEV_LAN_CIDR},gw=${DEV_LAN_GW}" \
      --ipconfig1 "ip=10.10.10.40/${PRIV_CIDR}" \
      --ciuser flowform --cipassword "rehearsal" \
      "${SSHKEYS_ARGS[@]}"
    qm start "${DEV_VMID}"
  fi
else
  log "dev box (240) skipped — set WITH_DEV_BOX=1 to create the operator workbench"
fi

log "done. VMs:"
qm list | awk 'NR==1 || $1 ~ /^(210|220|230|240)$/'
log "app-vm (220) has NO gateway by design — verify.sh asserts it can't reach the internet."
[[ "${WITH_DEV_BOX}" == "1" ]] && log "dev-vm (240) is an out-of-scope workbench at ${DEV_LAN_IP} (ssh flowform@${DEV_LAN_IP}); stop it for clean isolation runs."
