#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/packer-build.sh
. "${SCRIPT_DIR}/lib/packer-build.sh"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: build-proxmox-localstack-fixture.sh"
  echo "Build only the Proxmox LocalStack fixture derived from the golden template."
  exit 0
fi
[[ $# -eq 0 ]] || die "unexpected argument: $1"

vars_file="${PACKER_DIR}/variables/proxmox.auto.pkrvars.hcl"
require_vars_file "${vars_file}" "proxmox.auto.pkrvars.hcl.example"
assert_proxmox_build_ip_available "${vars_file}"
run_packer_build \
  "${PACKER_DIR}/builds/localstack-fixture.pkr.hcl" \
  "flowform-localstack-fixture.proxmox-clone.localstack_fixture" \
  "${vars_file}"
"${SCRIPT_DIR}/verify-proxmox-disk-sizes.sh" 8999 9000 9001
