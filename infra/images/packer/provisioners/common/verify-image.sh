#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
log "validating image dependencies"
command -v curl >/dev/null
command -v jq >/dev/null
command -v nft >/dev/null
docker --version
docker compose version
aws --version
test -d /opt/flowform
# Host convergence assets must be present and runnable; user data execs these
# directly and has no fallback if the image shipped without them.
test -x /opt/flowform/repo/infra/deployment/bootstrap/bootstrap-app.sh
test -x /opt/flowform/repo/infra/deployment/bootstrap/bootstrap-proxy.sh
test -f /opt/flowform/repo/infra/containers/runtime/compose/app.yml
test -f /opt/flowform/repo/infra/containers/runtime/compose/proxy.yml
test -f /opt/flowform/repo/infra/containers/strategies/aws/compose/proxy.override.yml
