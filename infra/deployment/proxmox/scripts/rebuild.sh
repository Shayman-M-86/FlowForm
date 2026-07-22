#!/usr/bin/env bash
set -Eeuo pipefail

# One-command Proxmox rehearsal (re)build. Convenience layer only — it adds no
# capability, it just runs the existing steps in the one order they can go in:
#
#   [destroy] -> apply -> build & push the backend image
#
# WHY THIS ORDER IS INHERENT (not a preference): the image push relays THROUGH
# the running app VM's Docker daemon (build-and-push-backend.sh streams the image
# over SSH to VM 220 and pushes from there via Squid). So the VM must exist and be
# healthy before the image can reach the registry — the push cannot precede the
# apply, and it cannot live inside Terraform. The app's bootstrap now WAITS for
# the image (retrying the pull) instead of hard-failing on the empty registry, so
# once the push lands the backend converges on its own: no manual re-bootstrap.
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
PUSH_SCRIPT="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/registry/build-and-push-backend.sh"

[[ -x "${WRAPPER}" ]]     || die "wrapper not found or not executable: ${WRAPPER}"
[[ -x "${PUSH_SCRIPT}" ]] || die "push script not found or not executable: ${PUSH_SCRIPT}"

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
  log "step 0/3: terraform destroy (--fresh) — wiping VMs, registry, seeded state"
  "${WRAPPER}" destroy "${APPLY_ARGS[@]}"
fi

log "step 1/3: terraform apply — clone/converge the rehearsal topology"
"${WRAPPER}" apply "${APPLY_ARGS[@]}"

log "step 2/3: build & push the backend image (relays through app VM 220)"
"${PUSH_SCRIPT}"

log "step 3/3: done. The app bootstrap waits for the image, so the backend"
log "  converges on its own now that the push has landed. Verify with:"
log "    curl --cacert ${REPO_ROOT}/infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt \\"
log "      https://api.localstack.test/api/v1/system/health/ready   # expect 200"
log "    ${HERE}/verify.sh                 # full egress model"
log "    ${HERE}/logs.sh app --list        # containers healthy"
