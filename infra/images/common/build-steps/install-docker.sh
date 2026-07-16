#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
log "installing Docker Engine and Compose plugin on Amazon Linux"
pkg_update
pkg_install docker containerd || pkg_install docker
if ! docker compose version >/dev/null 2>&1; then
  # AL2023 does not currently provide docker-compose-plugin, so install the
  # pinned upstream plugin when Compose is not already present.
  arch="$(uname -m)"
  case "$arch" in x86_64) compose_arch=x86_64 ;; aarch64|arm64) compose_arch=aarch64 ;; *) echo "unsupported arch ${arch}" >&2; exit 1 ;; esac
  install -d -m 0755 /usr/local/lib/docker/cli-plugins
  curl -fsSL "https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-${compose_arch}" -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod 0755 /usr/local/lib/docker/cli-plugins/docker-compose
fi
systemctl enable docker containerd || systemctl enable docker
