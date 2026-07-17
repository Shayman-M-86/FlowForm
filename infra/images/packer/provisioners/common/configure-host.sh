#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
log "applying common Amazon Linux host configuration"
cat >/etc/sysctl.d/99-flowform.conf <<'CONF'
net.ipv4.ip_forward = 0
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.tcp_syncookies = 1
CONF
sysctl --system >/dev/null
cat >/etc/cloud/cloud.cfg.d/99-flowform-runtime-only.cfg <<'CONF'
# FlowForm Packer images carry host dependencies; runtime cloud-init should not
# perform large package installs or upgrades during first boot.
package_update: false
package_upgrade: false
package_reboot_if_required: false
CONF
