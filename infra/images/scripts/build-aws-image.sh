#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/packer-build.sh
. "${SCRIPT_DIR}/lib/packer-build.sh"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: build-aws-image.sh"
  echo "Build only the AWS target from the shared golden Packer definition."
  exit 0
fi
[[ $# -eq 0 ]] || die "unexpected argument: $1"

vars_file="${PACKER_DIR}/variables/aws.auto.pkrvars.hcl"
require_vars_file "${vars_file}" "aws.auto.pkrvars.hcl.example"
run_packer_build \
  "${PACKER_DIR}/builds/golden.pkr.hcl" \
  "flowform-golden.amazon-ebs.amazon_linux_2023" \
  "${vars_file}"
