#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
log "installing Docker Engine and Compose plugin on Amazon Linux"
pkg_update
pkg_install docker containerd || pkg_install docker
compose_version=2.29.7
if ! docker compose version --short 2>/dev/null | grep -Eq "^v?${compose_version}$"; then
  pkg_install docker-compose-plugin || true
fi
if ! docker compose version --short 2>/dev/null | grep -Eq "^v?${compose_version}$"; then
  arch="$(uname -m)"
  case "$arch" in
    x86_64)
      compose_arch=x86_64
      compose_sha256=383ce6698cd5d5bbf958d2c8489ed75094e34a77d340404d9f32c4ae9e12baf0
      ;;
    aarch64|arm64)
      compose_arch=aarch64
      compose_sha256=6e9fbd5daa20dca5d7d89145081ae8155d68ef2928b497d9f85b54fe0f9dbb2c
      ;;
    *) echo "unsupported arch ${arch}" >&2; exit 1 ;;
  esac
  install -d -m 0755 /usr/local/lib/docker/cli-plugins
  compose_tmp="$(mktemp)"
  trap 'rm -f "${compose_tmp}"' EXIT
  curl -fsSL "https://github.com/docker/compose/releases/download/v${compose_version}/docker-compose-linux-${compose_arch}" -o "${compose_tmp}"
  printf '%s  %s\n' "${compose_sha256}" "${compose_tmp}" | sha256sum --check --status
  install -m 0755 "${compose_tmp}" /usr/local/lib/docker/cli-plugins/docker-compose
fi
systemctl enable docker containerd || systemctl enable docker
