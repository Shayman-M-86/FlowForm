#!/usr/bin/env bash
set -Eeuo pipefail

# One-command Proxmox rehearsal (re)build. Convenience layer only — it adds no
# capability, it just runs the existing steps in the one order they can go in:
#
#   [destroy] -> apply -> push backend image -> mirror grafana/alloy image
#
# WHY THIS ORDER IS INHERENT (not a preference): both image transfers relay
# THROUGH the running app VM's Docker daemon (build-and-push-backend.sh /
# mirror-alloy-image.sh stream the image over SSH to VM 220 and push from there
# via Squid). So the VM must exist and be healthy before an image can reach the
# registry — the transfers cannot precede the apply, and cannot live inside
# Terraform. The app's bootstrap now WAITS for the images (retrying the pull)
# instead of hard-failing on the empty registry, so once they land the backend
# converges on its own: no manual re-bootstrap.
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

[[ -x "${WRAPPER}" ]]      || die "wrapper not found or not executable: ${WRAPPER}"
[[ -x "${PUSH_SCRIPT}" ]]  || die "push script not found or not executable: ${PUSH_SCRIPT}"
[[ -x "${ALLOY_SCRIPT}" ]] || die "alloy mirror script not found or not executable: ${ALLOY_SCRIPT}"

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
  log "step 0/4: terraform destroy (--fresh) — wiping VMs, registry, seeded state"
  "${WRAPPER}" destroy "${APPLY_ARGS[@]}"
fi

log "step 1/4: terraform apply — clone/converge the rehearsal topology"
"${WRAPPER}" apply "${APPLY_ARGS[@]}"

log "step 2/4: build & push the backend image (relays through app VM 220)"
"${PUSH_SCRIPT}"

# The app's compose stack pulls TWO images the offline app box can only get from
# the fake registry: the backend AND grafana/alloy. Mirror Alloy too, or the
# app bootstrap's `compose pull` fails on the missing alloy image and never
# converges (compose pulls all services; one missing image fails the whole pull).
log "step 3/4: mirror the grafana/alloy image into the fake registry"
"${ALLOY_SCRIPT}"

log "step 4/4: done. The app bootstrap waits for both images, so the backend"
log "  converges on its own now that the pushes have landed. Verify with:"
log "    curl --cacert ${REPO_ROOT}/infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt \\"
log "      https://api.localstack.test/api/v1/system/health/ready   # expect 200"
log "    ${HERE}/verify.sh                 # full egress model"
log "    ${HERE}/logs.sh app --list        # containers healthy"
