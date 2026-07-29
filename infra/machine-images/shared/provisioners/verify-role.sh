#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh

role="${FLOWFORM_IMAGE_ROLE:?set FLOWFORM_IMAGE_ROLE to app or proxy}"
other_role="proxy"
[[ "${role}" == "proxy" ]] && other_role="app"

test -x /opt/flowform/runtime/common/scripts/run-role.sh
test -x /opt/flowform/runtime/common/scripts/load-release-manifest.sh
test -x /opt/flowform/host/bin/load-instance-context.sh
test -x "/opt/flowform/role/bin/bootstrap-${role}.sh"
test -f "/opt/flowform/runtime/compose/${role}.yml"
test -f "/etc/systemd/system/flowform-${role}.service"
systemctl is-enabled --quiet "flowform-${role}.service"

test ! -e "/opt/flowform/role/bin/bootstrap-${other_role}.sh"
test ! -e "/opt/flowform/runtime/compose/${other_role}.yml"
test ! -e "/etc/systemd/system/flowform-${other_role}.service"
test ! -e /opt/flowform/repo

grep -Fq '/etc/flowform/instance-context.json' /opt/flowform/host/bin/load-instance-context.sh
grep -Fq '/${role}/release' /opt/flowform/runtime/common/scripts/load-release-manifest.sh
log "validated ${role} role asset isolation"
