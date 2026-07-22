#!/usr/bin/env bash
set -Eeuo pipefail

# One-command Proxmox rehearsal (re)build. Convenience layer only — it adds no
# capability, it just runs the existing steps in the one order they can go in:
#
#   [destroy] -> apply -> push backend image -> mirror grafana/alloy image
#             -> converge app
#
# WHY THIS ORDER IS INHERENT (not a preference): both image transfers relay
# THROUGH the running app VM's Docker daemon (build-and-push-backend.sh /
# mirror-alloy-image.sh stream the image over SSH to VM 220 and push from there
# via Squid). So the VM must exist and be healthy before an image can reach the
# registry — the transfers cannot precede the apply, and cannot live inside
# Terraform. The app bootstrap waits for the images, but that wait is bounded;
# a slow first boot or image build can outlast it. After both pushes, this script
# explicitly reruns the idempotent app bootstrap to close that timing window.
#
# BOTH images are required: the app compose stack pulls the backend AND
# grafana/alloy, and the offline app box can fetch neither from the internet —
# only from the fake registry. Omitting the Alloy mirror leaves `compose pull`
# failing forever on the missing alloy image (a whole-stack pull fails if any one
# service image is absent), which looks exactly like a stuck backend pull.
#
# Usage:
#   rebuild.sh                 converge the stack (idempotent apply) + push image
#   rebuild.sh --fresh         terraform destroy FIRST (full teardown+rebuild:
#                              wipes VMs, registry contents, and all seeded state),
#                              then apply + push
#   rebuild.sh -- -auto-approve   pass everything after `--` to the terraform apply
#
# --fresh is opt-in on purpose: a bare rebuild.sh must never destroy a healthy
# stack. Combine them, e.g.:  rebuild.sh --fresh -- -auto-approve
#
# Prerequisites are the same as with-dev-auth0-env.sh (which this calls): the
# Auth0/Grafana env files, a valid `aws login` for the mgmt secret, tfvars, and
# ssh-agent access to the Proxmox node. That wrapper does its own preflight.

log() { printf '[rebuild] %s\n' "$*" >&2; }
die() { printf '[rebuild] ERROR: %s\n' "$*" >&2; exit 1; }

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER="${HERE}/with-dev-auth0-env.sh"
REPO_ROOT="$(cd -- "${HERE}/../../../.." && pwd)"
REGISTRY_DIR="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/registry"
PUSH_SCRIPT="${REGISTRY_DIR}/build-and-push-backend.sh"
ALLOY_SCRIPT="${REGISTRY_DIR}/mirror-alloy-image.sh"
PVE_SSH_TARGET="${PROXMOX_SSH_TARGET:-root@192.168.68.88}"
PVE_SSH_KEY="${PROXMOX_SSH_KEY:-${HOME}/.ssh/proxmox_codex}"
PVE_PRIVATE_BRIDGE="${PROXMOX_PRIVATE_BRIDGE:-vmbr10}"
PVE_TEMP_BRIDGE_CIDR="${PROXMOX_TEMP_BRIDGE_CIDR:-10.10.10.1/24}"
APP_SSH_TARGET="${PUSH_RELAY_SSH_TARGET:-ec2-user@10.10.10.20}"

[[ -x "${WRAPPER}" ]]      || die "wrapper not found or not executable: ${WRAPPER}"
[[ -x "${PUSH_SCRIPT}" ]]  || die "push script not found or not executable: ${PUSH_SCRIPT}"
[[ -x "${ALLOY_SCRIPT}" ]] || die "alloy mirror script not found or not executable: ${ALLOY_SCRIPT}"
[[ -r "${PVE_SSH_KEY}" ]]  || die "Proxmox SSH key not readable: ${PVE_SSH_KEY}"

converge_app() (
  local bridge_added=0
  local -a ssh_options=(
    -i "${PVE_SSH_KEY}"
    -o BatchMode=yes
    -o ConnectTimeout=10
  )

  cleanup_bridge() {
    if (( bridge_added == 1 )); then
      ssh "${ssh_options[@]}" "${PVE_SSH_TARGET}" \
        "ip address del '${PVE_TEMP_BRIDGE_CIDR}' dev '${PVE_PRIVATE_BRIDGE}'" \
        >/dev/null 2>&1 \
        || log "WARNING: could not remove ${PVE_TEMP_BRIDGE_CIDR} from ${PVE_PRIVATE_BRIDGE}"
    fi
  }
  trap cleanup_bridge EXIT INT TERM HUP

  if ! ssh "${ssh_options[@]}" "${PVE_SSH_TARGET}" \
    "ip -4 -o address show dev '${PVE_PRIVATE_BRIDGE}' | awk '{print \$4}' | grep -Fqx '${PVE_TEMP_BRIDGE_CIDR}'"; then
    ssh "${ssh_options[@]}" "${PVE_SSH_TARGET}" \
      "ip address add '${PVE_TEMP_BRIDGE_CIDR}' dev '${PVE_PRIVATE_BRIDGE}'"
    bridge_added=1
  fi

  ssh "${ssh_options[@]}" \
    -o UserKnownHostsFile=/dev/null \
    -o StrictHostKeyChecking=no \
    -o "ProxyCommand=ssh -i ${PVE_SSH_KEY} -o BatchMode=yes -W %h:%p ${PVE_SSH_TARGET}" \
    "${APP_SSH_TARGET}" \
    'sudo /opt/flowform/scripts/run-bootstrap-app.sh'
)

FRESH=0
APPLY_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fresh) FRESH=1; shift ;;
    --) shift; APPLY_ARGS+=("$@"); break ;;
    -h|--help) sed -n '/^# /{s/^# \{0,1\}//p;}' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) die "unknown argument: $1 (did you mean to put terraform args after '--'?)" ;;
  esac
done

if (( FRESH == 1 )); then
  log "step 0/5: terraform destroy (--fresh) — wiping VMs, registry, seeded state"
  "${WRAPPER}" destroy "${APPLY_ARGS[@]}"
fi

log "step 1/5: terraform apply — clone/converge the rehearsal topology"
"${WRAPPER}" apply "${APPLY_ARGS[@]}"

log "step 2/5: build & push the backend image (relays through app VM 220)"
"${PUSH_SCRIPT}"

# The app's compose stack pulls TWO images the offline app box can only get from
# the fake registry: the backend AND grafana/alloy. Mirror Alloy too, or the
# app bootstrap's `compose pull` fails on the missing alloy image and never
# converges (compose pulls all services; one missing image fails the whole pull).
log "step 3/5: mirror the grafana/alloy image into the fake registry"
"${ALLOY_SCRIPT}"

log "step 4/5: converge the app after both images are present"
converge_app

log "step 5/5: done. Verify with:"
log "    curl --cacert ${REPO_ROOT}/infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt \\"
log "      https://api.localstack.test/api/v1/system/health/ready   # expect 200"
log "    ${HERE}/verify.sh                 # full egress model"
log "    ${HERE}/logs.sh app --list        # containers healthy"
