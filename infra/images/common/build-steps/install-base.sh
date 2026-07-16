#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
log "installing Amazon Linux base packages"
pkg_update
pkg_install ca-certificates curl-minimal jq unzip nftables openssl shadow-utils systemd-networkd || pkg_install ca-certificates curl-minimal jq unzip nftables openssl shadow-utils
install -d -m 0755 /opt/flowform /etc/flowform /var/lib/flowform
systemctl enable nftables || true
