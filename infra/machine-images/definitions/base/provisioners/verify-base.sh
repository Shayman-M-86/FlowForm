#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh

log "validating base image dependencies and ownership boundary"

command -v aws >/dev/null
command -v curl >/dev/null
command -v docker >/dev/null
command -v jq >/dev/null
command -v nft >/dev/null
docker compose version >/dev/null
rpm -q ec2-instance-connect >/dev/null
test -d /opt/flowform

# A base image is never directly launched by CDK and must not carry either
# host role. Child AMIs install exactly one of these trees.
test ! -e /opt/flowform/role
test ! -e /opt/flowform/host
test ! -e /opt/flowform/runtime
test ! -e /etc/systemd/system/flowform-app.service
test ! -e /etc/systemd/system/flowform-proxy.service
