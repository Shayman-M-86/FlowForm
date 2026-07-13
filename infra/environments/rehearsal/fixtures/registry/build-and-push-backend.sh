#!/usr/bin/env bash
set -Eeuo pipefail

# Build the FlowForm backend image and push it to the rehearsal's private
# registry, so the offline app box (220) can pull it at bootstrap — mirroring how
# real EC2 pulls BACKEND_IMAGE from ECR and never from the internet.
#
# WHERE THIS RUNS: the dev box (240) — the dual-homed operator workbench. It has
# internet (to pull the base image + uv), reaches the registry on the private net
# (10.10.10.30:5000), and has Docker + the repo. It is NOT part of the isolation
# under test; it's the human's staging hands. (You can also run it from any host
# with Docker + a route to the registry and a repo checkout.)
#
# WHAT IT PROVES / DOESN'T: this is the rehearsal stand-in for the ECR push half
# of a deploy. It is a REHEARSAL delta — plain HTTP registry, no ECR auth, no
# image signing. The real push path (ECR + IAM + S3 gateway for layers) is
# staging's job. Never read a green push here as proof of the ECR path.
#
# Prod fidelity: builds with --no-dev (the prod runtime image — no dev tooling),
# NOT the dev-extra build. The app box runs exactly this image.
#
# Idempotent: re-running rebuilds (Docker layer cache makes it cheap) and
# re-pushes; an unchanged image is a no-op push.

REGISTRY="${REGISTRY:-10.10.10.30:5000}"
IMAGE_NAME="${IMAGE_NAME:-flowform-backend}"
IMAGE_TAG="${IMAGE_TAG:-rehearsal}"
DEST="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

log() { printf '[build-push-backend] %s\n' "$*"; }
die() { printf '[build-push-backend] ERROR: %s\n' "$*" >&2; exit 1; }

# Locate the repo root from this script (fixtures/registry -> ../../../.. ). Allow
# REPO_ROOT override for odd checkouts.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)}"

DOCKERFILE="${REPO_ROOT}/infra/environments/development/compose/backend.Dockerfile"
[[ -f "${DOCKERFILE}" ]] || die "backend Dockerfile not found at ${DOCKERFILE} (REPO_ROOT=${REPO_ROOT}; sync the repo to the dev box or set REPO_ROOT=)"
command -v docker >/dev/null 2>&1 || die "docker not found on this box"

# Registry must be up (fake ECR on the aws-fixtures-vm, 230). Fail early clearly.
if ! curl -fsS "http://${REGISTRY}/v2/" >/dev/null 2>&1; then
  die "registry not reachable at http://${REGISTRY}/v2/ — is the aws-fixtures-vm (230) up? registry:2 auto-starts there via flowform-registry.service (baked into template 9001)."
fi

log "building ${DEST} from ${DOCKERFILE} (context=${REPO_ROOT}, --no-dev prod image)"
# Default UV_SYNC_FLAGS in the Dockerfile is already --no-dev; pass explicitly to
# make the prod-runtime intent unmistakable and immune to a Dockerfile default change.
docker build \
  -f "${DOCKERFILE}" \
  --build-arg UV_SYNC_FLAGS="--no-dev" \
  -t "${DEST}" \
  "${REPO_ROOT}"

log "pushing ${DEST}"
docker push "${DEST}"

log "done. Registry catalog:"
curl -fsS "http://${REGISTRY}/v2/_catalog" | sed 's/^/  /'
log "app box (220) BACKEND_IMAGE should be: ${DEST}"
