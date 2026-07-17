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

source_ami_name="$(awk -F '"' '$1 ~ /^[[:space:]]*aws_source_ami_name[[:space:]]*=/ { print $2; exit }' "${vars_file}")"
source_ami_owner="$(awk -F '"' '$1 ~ /^[[:space:]]*aws_source_ami_owner[[:space:]]*=/ { print $2; exit }' "${vars_file}")"
architecture="$(awk -F '"' '$1 ~ /^[[:space:]]*aws_architecture[[:space:]]*=/ { print $2; exit }' "${vars_file}")"
root_volume_size="$(awk -F '=' '$1 ~ /^[[:space:]]*aws_root_volume_size[[:space:]]*$/ { gsub(/[[:space:]]/, "", $2); print $2; exit }' "${vars_file}")"
[[ "${source_ami_owner}" == "amazon" ]] \
  || die "aws_source_ami_owner must be the verified Amazon owner alias"
[[ "${source_ami_name}" == al2023-ami-minimal-2023.*-kernel-6.1-x86_64 ]] \
  || die "aws_source_ami_name must select the x86_64 AL2023 minimal kernel-6.1 AMI"
[[ "${architecture}" == "x86_64" ]] || die "aws_architecture must be x86_64"
[[ "${root_volume_size}" =~ ^[0-9]+$ ]] \
  || die "aws_root_volume_size must be an integer GiB value"
(( root_volume_size >= 8 && root_volume_size <= 12 )) \
  || die "aws_root_volume_size must be between 8 and 12 GiB"

run_packer_build \
  "${PACKER_DIR}/builds/golden.pkr.hcl" \
  "flowform-golden.amazon-ebs.amazon_linux_2023" \
  "${vars_file}"
"${SCRIPT_DIR}/verify-aws-ami.sh" --vars-file "${vars_file}"
