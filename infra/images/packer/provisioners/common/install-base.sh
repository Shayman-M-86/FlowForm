#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
log "installing Amazon Linux base packages"
pkg_update
# util-linux-core provides flock, which the bootstrap scripts use as a single-
# instance guard (cloud-init / systemd / manual deploy must not race). Everything
# else the bootstraps need (jq, curl, openssl, nft, timeout from coreutils) is
# already present in the base.
pkg_install ca-certificates curl-minimal jq unzip nftables openssl shadow-utils util-linux-core systemd-networkd || pkg_install ca-certificates curl-minimal jq unzip nftables openssl shadow-utils util-linux-core
install -d -m 0755 /opt/flowform /etc/flowform /var/lib/flowform
systemctl enable nftables || true
