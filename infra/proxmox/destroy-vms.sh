#!/usr/bin/env bash
set -Eeuo pipefail

# Tear down the three rehearsal VMs (run ON the PVE host). The golden template
# (9000) and the host bridges are KEPT — re-run create-vms.sh to rebuild the
# VMs cheaply from the template.
#
# Safe: only touches VMIDs 210/220/230/240. Never touches templates
# (9000/9001/9002), vmbr0, vmbr10, or VM 100.

VMIDS=(210 220 230 240)

log() { printf '[destroy-vms] %s\n' "$*"; }

for vmid in "${VMIDS[@]}"; do
  if qm status "${vmid}" >/dev/null 2>&1; then
    log "stopping + destroying ${vmid}"
    qm stop "${vmid}" >/dev/null 2>&1 || true
    qm destroy "${vmid}" --purge
  else
    log "${vmid} not present — skipping"
  fi
done

log "done. Template 9000 and bridges kept."
