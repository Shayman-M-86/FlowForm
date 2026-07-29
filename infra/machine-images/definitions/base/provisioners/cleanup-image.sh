#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
log "cleaning image state"
"$FLOWFORM_PKG" clean all || true
rm -rf /var/cache/dnf /var/cache/yum /tmp/* /var/tmp/*
rm -f /var/log/flowform-packer-boot.log
cloud-init clean --logs || true
truncate -s 0 /etc/machine-id || true
rm -f /var/lib/dbus/machine-id
history -c || true
