#!/usr/bin/env bash
# TODO(migration): Update paths, contracts, and runtime wiring for infra-new before this file is used.
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
log "cleaning image state"
"$FLOWFORM_PKG" clean all || true
rm -rf /var/cache/dnf /var/cache/yum /tmp/* /var/tmp/*
cloud-init clean --logs || true
truncate -s 0 /etc/machine-id || true
rm -f /var/lib/dbus/machine-id
history -c || true
