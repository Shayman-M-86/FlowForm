#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/packer-build.sh
. "${SCRIPT_DIR}/lib/packer-build.sh"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: build-proxmox-image.sh"
  echo "Build only the Proxmox target from the shared golden Packer definition."
  exit 0
fi
[[ $# -eq 0 ]] || die "unexpected argument: $1"

vars_file="${PACKER_DIR}/variables/proxmox.auto.pkrvars.hcl"
require_vars_file "${vars_file}" "proxmox.auto.pkrvars.hcl.example"
assert_proxmox_build_ip_available "${vars_file}"
run_packer_build \
  "${PACKER_DIR}/builds/golden.pkr.hcl" \
  "flowform-golden.proxmox-clone.amazon_linux_2023" \
  "${vars_file}"
"${SCRIPT_DIR}/verify-proxmox-disk-sizes.sh" 8999 9000
