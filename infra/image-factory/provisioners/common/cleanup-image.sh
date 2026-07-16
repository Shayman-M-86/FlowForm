#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
log "cleaning image state"
"$FLOWFORM_PKG" clean all || true
rm -rf /var/cache/dnf /var/cache/yum /tmp/* /var/tmp/*
cloud-init clean --logs --seed || true
truncate -s 0 /etc/machine-id || true
rm -f /var/lib/dbus/machine-id
rm -f /etc/ssh/ssh_host_*
rm -f /root/.ssh/authorized_keys /home/ec2-user/.ssh/authorized_keys
rm -f /tmp/flowform-image-lib.sh
history -c || true
