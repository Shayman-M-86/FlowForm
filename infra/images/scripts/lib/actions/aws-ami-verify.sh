#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKER_DIR="${PACKER_DIR:-$(cd -- "${SCRIPT_DIR}/../../../packer" && pwd)}"
VARS_FILE="${PACKER_DIR}/variables/aws.auto.pkrvars.hcl"
MANIFEST="${PACKER_DIR}/manifests/packer-manifest.json"

usage() {
  cat <<'USAGE'
Usage: image verify aws [--vars-file PATH] [--manifest PATH]

Verify that the most recent amazon-ebs artifact has exactly the configured
root volume size, uses gp3, is encrypted, and has no additional EBS mappings.
USAGE
}

die() {
  printf '[image-aws-verify] ERROR: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vars-file)
      [[ $# -ge 2 ]] || die "--vars-file requires a path"
      VARS_FILE="$2"
      shift 2
      ;;
    --manifest)
      [[ $# -ge 2 ]] || die "--manifest requires a path"
      MANIFEST="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *) die "unknown argument: $1" ;;
  esac
done

for command_name in aws jq; do
  command -v "${command_name}" >/dev/null 2>&1 || die "required command not found: ${command_name}"
done
[[ -f "${VARS_FILE}" ]] || die "Packer variables file not found: ${VARS_FILE}"
[[ -f "${MANIFEST}" ]] || die "Packer manifest not found: ${MANIFEST}"

read_string_assignment() {
  local name="$1"
  awk -F '"' -v name="${name}" '$1 ~ "^[[:space:]]*" name "[[:space:]]*=" { print $2; exit }' "${VARS_FILE}"
}

read_number_assignment() {
  local name="$1"
  awk -F '=' -v name="${name}" '$1 ~ "^[[:space:]]*" name "[[:space:]]*$" { gsub(/[[:space:]]/, "", $2); print $2; exit }' "${VARS_FILE}"
}

region="$(read_string_assignment aws_region)"
source_ami_name="$(read_string_assignment aws_source_ami_name)"
source_ami_owner="$(read_string_assignment aws_source_ami_owner)"
architecture="$(read_string_assignment aws_architecture)"
expected_size="$(read_number_assignment aws_root_volume_size)"
expected_encrypted="$(awk -F '=' '$1 ~ /^[[:space:]]*aws_encrypt_boot[[:space:]]*$/ { gsub(/[[:space:]]/, "", $2); print $2; exit }' "${VARS_FILE}")"
[[ -n "${region}" ]] || die "aws_region is missing from ${VARS_FILE}"
[[ "${source_ami_owner}" == "amazon" ]] \
  || die "aws_source_ami_owner is not the verified Amazon alias: ${source_ami_owner}"
[[ "${source_ami_name}" == al2023-ami-minimal-2023.*-kernel-6.1-x86_64 ]] \
  || die "aws_source_ami_name does not select x86_64 AL2023 minimal kernel 6.1: ${source_ami_name}"
[[ "${architecture}" == "x86_64" ]] || die "aws_architecture must be x86_64"
[[ "${expected_size}" =~ ^[0-9]+$ ]] || die "aws_root_volume_size must be numeric"
(( expected_size >= 8 && expected_size <= 12 )) \
  || die "aws_root_volume_size must be between 8 and 12 GiB"
[[ "${expected_encrypted}" == "true" ]] \
  || die "aws_encrypt_boot must remain true for the FlowForm AWS image contract"

ami_id="$(jq -er '
  .builds | map(select(.builder_type == "amazon-ebs")) | last | .artifact_id // empty
  | select(type == "string") | split(":") | .[1] // empty
' "${MANIFEST}")" || die "no amazon-ebs artifact found in ${MANIFEST}"
[[ "${ami_id}" =~ ^ami-[0-9a-f]+$ ]] || die "invalid amazon-ebs artifact ID: ${ami_id}"

image_json="$(aws ec2 describe-images --region "${region}" --image-ids "${ami_id}" --output json)"
[[ "$(jq -r '.Images | length' <<<"${image_json}")" == "1" ]] \
  || die "AMI ${ami_id} was not found in ${region}"
[[ "$(jq -r '.Images[0].State' <<<"${image_json}")" == "available" ]] \
  || die "AMI ${ami_id} is not available"
[[ "$(jq -r '.Images[0].Architecture' <<<"${image_json}")" == "x86_64" ]] \
  || die "AMI ${ami_id} is not x86_64"
[[ "$(jq -r '.Images[0].RootDeviceType' <<<"${image_json}")" == "ebs" ]] \
  || die "AMI ${ami_id} is not EBS-backed"
[[ "$(jq -r '.Images[0].VirtualizationType' <<<"${image_json}")" == "hvm" ]] \
  || die "AMI ${ami_id} is not HVM"

root_device="$(jq -r '.Images[0].RootDeviceName' <<<"${image_json}")"
ebs_count="$(jq '[.Images[0].BlockDeviceMappings[] | select(.Ebs != null)] | length' <<<"${image_json}")"
[[ "${ebs_count}" == "1" ]] || die "AMI ${ami_id} has ${ebs_count} EBS mappings; expected only the root"

root_mapping="$(jq -c --arg device "${root_device}" '.Images[0].BlockDeviceMappings[] | select(.DeviceName == $device and .Ebs != null) | .Ebs' <<<"${image_json}")"
[[ -n "${root_mapping}" ]] || die "root EBS mapping ${root_device} was not found"
actual_size="$(jq -r '.VolumeSize' <<<"${root_mapping}")"
volume_type="$(jq -r '.VolumeType' <<<"${root_mapping}")"
encrypted="$(jq -r '.Encrypted' <<<"${root_mapping}")"
snapshot_id="$(jq -r '.SnapshotId' <<<"${root_mapping}")"

[[ "${actual_size}" == "${expected_size}" ]] \
  || die "AMI root is ${actual_size} GiB; expected exactly ${expected_size} GiB"
[[ "${volume_type}" == "gp3" ]] || die "AMI root volume type is ${volume_type}; expected gp3"
[[ "${encrypted}" == "true" ]] || die "AMI root snapshot is not encrypted"
[[ "${snapshot_id}" =~ ^snap-[0-9a-f]+$ ]] || die "AMI root snapshot ID is invalid: ${snapshot_id}"

snapshot_json="$(aws ec2 describe-snapshots --region "${region}" --snapshot-ids "${snapshot_id}" --output json)"
[[ "$(jq -r '.Snapshots[0].VolumeSize' <<<"${snapshot_json}")" == "${expected_size}" ]] \
  || die "root snapshot does not have the expected ${expected_size} GiB volume size"
[[ "$(jq -r '.Snapshots[0].Encrypted' <<<"${snapshot_json}")" == "true" ]] \
  || die "root snapshot is not encrypted"

printf 'ami=%s\tregion=%s\troot=%s\tsize=%sGiB\ttype=%s\tencrypted=%s\tsnapshot=%s\tsource-filter=%s\n' \
  "${ami_id}" "${region}" "${root_device}" "${actual_size}" "${volume_type}" \
  "${encrypted}" "${snapshot_id}" "${source_ami_name}"
