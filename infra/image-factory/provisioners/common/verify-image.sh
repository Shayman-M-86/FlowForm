#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
log "validating image dependencies"
command -v curl >/dev/null
command -v jq >/dev/null
command -v nft >/dev/null
docker --version
docker compose version
/usr/local/bin/aws --version || aws --version
test -d /opt/flowform
