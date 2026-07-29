#!/usr/bin/env bash
# TODO(migration): Update paths, contracts, and runtime wiring for infra-new before this file is used.
set -Eeuo pipefail
log() { printf '[flowform-image] %s\n' "$*"; }
die() {
  printf '[flowform-image] ERROR: %s\n' "$*" >&2
  exit 1
}
if command -v dnf >/dev/null 2>&1; then
  export FLOWFORM_PKG=dnf
elif command -v yum >/dev/null 2>&1; then
  export FLOWFORM_PKG=yum
else
  echo "No supported package manager found (expected dnf/yum for Amazon Linux)" >&2
  exit 1
fi
pkg_install() {
  "$FLOWFORM_PKG" install -y "$@"
}
pkg_update() {
  "$FLOWFORM_PKG" makecache -y
}
