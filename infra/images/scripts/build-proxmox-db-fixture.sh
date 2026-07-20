#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/packer-build.sh
. "${SCRIPT_DIR}/lib/packer-build.sh"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: build-proxmox-db-fixture.sh"
  echo "Build the Proxmox PostgreSQL fixture derived from the golden template."
  exit 0
fi
[[ $# -eq 0 ]] || die "unexpected argument: $1"

vars_file="${PACKER_DIR}/variables/proxmox.auto.pkrvars.hcl"
require_vars_file "${vars_file}" "proxmox.auto.pkrvars.hcl.example"
assert_proxmox_build_ip_available "${vars_file}"
run_packer_build \
  "${PACKER_DIR}/builds/db-fixture.pkr.hcl" \
  "flowform-db-fixture.proxmox-clone.db_fixture" \
  "${vars_file}"
[[ "${PACKER_VALIDATE_ONLY:-0}" == "1" ]] && exit 0
"${SCRIPT_DIR}/verify-proxmox-disk-sizes.sh" 8999 9000 9001 9002
