#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: destroy-vms.sh [--purge-state]

Destroys only VMIDs recorded in the FlowForm rehearsal state. The selected
golden template and host bridges are retained. --purge-state also removes the
orchestration key, staged artifacts, and activation state.
USAGE
}

log() { printf '[destroy-vms] %s\n' "$*"; }
die() { printf '[destroy-vms] ERROR: %s\n' "$*" >&2; exit 1; }

STATE_DIR="${FLOWFORM_REHEARSAL_STATE_DIR:-/var/lib/flowform/rehearsal}"
STATE_FILE="${STATE_DIR}/state.json"
purge_state=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge-state) purge_state=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ "${EUID}" -eq 0 || "${FLOWFORM_TEST_MODE:-0}" == "1" ]] || die "run as root on the Proxmox host"
command -v qm >/dev/null 2>&1 || die "qm not found"
command -v jq >/dev/null 2>&1 || die "jq not found"
[[ -f "${STATE_FILE}" ]] || die "state file not found: ${STATE_FILE}; refusing an unscoped destroy"
jq -e '.schema == "flowform.rehearsal-state/1" and (.vmids | type == "array")' "${STATE_FILE}" >/dev/null \
  || die "invalid rehearsal state: ${STATE_FILE}"

mapfile -t vmids < <(jq -r '.vmids[]' "${STATE_FILE}")
for vmid in "${vmids[@]}"; do
  [[ "${vmid}" =~ ^(210|220|230|240)$ ]] || die "state contains unexpected VMID ${vmid}; refusing"
  if qm status "${vmid}" >/dev/null 2>&1; then
    log "stopping and destroying ${vmid}"
    qm stop "${vmid}" >/dev/null 2>&1 || true
    qm destroy "${vmid}" --purge
  else
    log "${vmid} already absent"
  fi
done

if [[ "${purge_state}" == "1" ]]; then
  rm -rf --one-file-system "${STATE_DIR}"
  log "purged ${STATE_DIR}"
else
  tmp="$(mktemp "${STATE_FILE}.tmp.XXXXXX")"
  jq '.status = "destroyed" | .destroyed_at = (now | todateiso8601)' "${STATE_FILE}" > "${tmp}"
  mv "${tmp}" "${STATE_FILE}"
  chmod 0600 "${STATE_FILE}"
fi
log "done; golden template and bridges retained"
