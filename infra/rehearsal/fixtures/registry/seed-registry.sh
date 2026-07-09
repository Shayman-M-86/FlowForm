#!/usr/bin/env bash
set -Eeuo pipefail

# Seed the rehearsal's private registry (run ON proxy-vm / 10.10.10.10).
#
# The proxy is the only VM with internet. This pulls the public images the
# offline VMs need and re-pushes them to the private registry at
# 10.10.10.10:5000, so app-vm/ls-vm can pull without ever touching the internet.
#
# Idempotent: re-pushing an unchanged image is a cheap no-op.

REGISTRY="${REGISTRY:-10.10.10.10:5000}"

# public image  ->  private tag (same basename under the private registry)
IMAGES=(
  "localstack/localstack:3"
)

log() { printf '[seed-registry] %s\n' "$*"; }
die() { printf '[seed-registry] ERROR: %s\n' "$*" >&2; exit 1; }

# Registry must be up.
curl -fsS "http://${REGISTRY}/v2/" >/dev/null 2>&1 \
  || die "registry not reachable at http://${REGISTRY}/v2/ — start docker-compose.registry.yml first"

for src in "${IMAGES[@]}"; do
  dst="${REGISTRY}/${src}"
  log "pull ${src}"
  docker pull "${src}"
  log "tag  ${src} → ${dst}"
  docker tag "${src}" "${dst}"
  log "push ${dst}"
  docker push "${dst}"
done

log "done. Private images:"
curl -fsS "http://${REGISTRY}/v2/_catalog" | sed 's/^/  /'
