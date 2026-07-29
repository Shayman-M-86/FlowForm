#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKER_DIR="${PACKER_DIR:-$(cd -- "${SCRIPT_DIR}/../../../packer" && pwd)}"
VARS_FILE="${PACKER_DIR}/variables/aws.auto.pkrvars.hcl"
MANIFEST=""
ROLE="base"
PARENT_AMI_ID=""

usage() {
  cat <<'USAGE'
Usage: image verify aws <base|app|proxy> [--vars-file PATH] [--manifest PATH]
       [--parent-ami-id AMI]

Verify the selected AMI's lineage, tags, architecture, and encrypted gp3 root
snapshot. Successful verification records the resolved AMI and snapshot in the
generated Packer manifest.
USAGE
}

die() {
  printf '[image-aws-verify] ERROR: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      [[ $# -ge 2 ]] || die "--role requires a value"
      ROLE="$2"
      shift 2
      ;;
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
    --parent-ami-id)
      [[ $# -ge 2 ]] || die "--parent-ami-id requires a value"
      PARENT_AMI_ID="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ "${ROLE}" =~ ^(base|app|proxy)$ ]] || die "role must be base, app, or proxy"
MANIFEST="${MANIFEST:-${PACKER_DIR}/manifests/${ROLE}-manifest.json}"

for command_name in aws jq; do
  command -v "${command_name}" >/dev/null 2>&1 \
    || die "required command not found: ${command_name}"
done
[[ -f "${VARS_FILE}" ]] || die "Packer variables file not found: ${VARS_FILE}"
[[ -f "${MANIFEST}" ]] || die "Packer manifest not found: ${MANIFEST}"

read_string_assignment() {
  local name="$1"
  awk -F '"' -v name="${name}" \
    '$1 ~ "^[[:space:]]*" name "[[:space:]]*=" { print $2; exit }' \
    "${VARS_FILE}"
}

read_number_assignment() {
  local name="$1"
  awk -F '=' -v name="${name}" \
    '$1 ~ "^[[:space:]]*" name "[[:space:]]*$" {
      gsub(/[[:space:]]/, "", $2)
      print $2
      exit
    }' "${VARS_FILE}"
}

region="$(read_string_assignment aws_region)"
source_ami_name="$(read_string_assignment aws_source_ami_name)"
source_ami_owner="$(read_string_assignment aws_source_ami_owner)"
architecture="$(read_string_assignment aws_architecture)"
expected_size="$(read_number_assignment aws_root_volume_size)"
expected_encrypted="$(
  awk -F '=' \
    '$1 ~ /^[[:space:]]*aws_encrypt_boot[[:space:]]*$/ {
      gsub(/[[:space:]]/, "", $2)
      print $2
      exit
    }' "${VARS_FILE}"
)"

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

build_json="$(
  jq -ec '
    .builds
    | map(select(.builder_type == "amazon-ebs"))
    | last
    | select(type == "object")
  ' "${MANIFEST}"
)" || die "no amazon-ebs artifact found in ${MANIFEST}"

ami_id="$(jq -er '.artifact_id | split(":") | .[1] // empty' <<<"${build_json}")" \
  || die "no AMI ID found in ${MANIFEST}"
[[ "${ami_id}" =~ ^ami-[0-9a-f]+$ ]] || die "invalid amazon-ebs artifact ID: ${ami_id}"

manifest_role="$(jq -r '.custom_data.image_role // empty' <<<"${build_json}")"
source_commit="$(jq -r '.custom_data.source_commit // empty' <<<"${build_json}")"
manifest_parent="$(jq -r '.custom_data.parent_ami_id // empty' <<<"${build_json}")"
[[ "${manifest_role}" == "${ROLE}" ]] \
  || die "manifest image role is ${manifest_role:-missing}; expected ${ROLE}"
[[ "${source_commit}" =~ ^[0-9a-f]{40}$ ]] \
  || die "manifest source commit is missing or invalid"

if [[ "${ROLE}" == "base" ]]; then
  [[ -z "${PARENT_AMI_ID}" ]] || die "base AMIs do not accept --parent-ami-id"
  [[ -z "${manifest_parent}" ]] || die "base manifest unexpectedly records a parent AMI"
else
  PARENT_AMI_ID="${PARENT_AMI_ID:-${manifest_parent}}"
  [[ "${PARENT_AMI_ID}" =~ ^ami-[0-9a-f]+$ ]] \
    || die "${ROLE} manifest parent AMI is missing or invalid"
  [[ "${manifest_parent}" == "${PARENT_AMI_ID}" ]] \
    || die "${ROLE} manifest parent ${manifest_parent:-missing} does not match ${PARENT_AMI_ID}"
fi

image_json="$(
  aws ec2 describe-images \
    --region "${region}" \
    --image-ids "${ami_id}" \
    --output json \
    --no-cli-pager
)"
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

tag_value() {
  local key="$1"
  jq -r --arg key "${key}" \
    '.Images[0].Tags // [] | map(select(.Key == $key)) | first.Value // empty' \
    <<<"${image_json}"
}

[[ "$(tag_value project)" == "flowform" ]] || die "AMI ${ami_id} is not tagged project=flowform"
[[ "$(tag_value managed_by)" == "packer" ]] || die "AMI ${ami_id} is not tagged managed_by=packer"
[[ "$(tag_value image_role)" == "${ROLE}" ]] \
  || die "AMI ${ami_id} does not carry image_role=${ROLE}"
[[ "$(tag_value source_commit)" == "${source_commit}" ]] \
  || die "AMI ${ami_id} source_commit tag does not match its manifest"
if [[ "${ROLE}" != "base" ]]; then
  [[ "$(tag_value parent_ami_id)" == "${PARENT_AMI_ID}" ]] \
    || die "AMI ${ami_id} parent_ami_id tag does not match ${PARENT_AMI_ID}"
fi

root_device="$(jq -r '.Images[0].RootDeviceName' <<<"${image_json}")"
ebs_count="$(
  jq '[.Images[0].BlockDeviceMappings[] | select(.Ebs != null)] | length' \
    <<<"${image_json}"
)"
[[ "${ebs_count}" == "1" ]] \
  || die "AMI ${ami_id} has ${ebs_count} EBS mappings; expected only the root"

root_mapping="$(
  jq -c --arg device "${root_device}" \
    '.Images[0].BlockDeviceMappings[]
     | select(.DeviceName == $device and .Ebs != null)
     | .Ebs' \
    <<<"${image_json}"
)"
[[ -n "${root_mapping}" ]] || die "root EBS mapping ${root_device} was not found"
actual_size="$(jq -r '.VolumeSize' <<<"${root_mapping}")"
volume_type="$(jq -r '.VolumeType' <<<"${root_mapping}")"
encrypted="$(jq -r '.Encrypted' <<<"${root_mapping}")"
snapshot_id="$(jq -r '.SnapshotId' <<<"${root_mapping}")"

[[ "${actual_size}" == "${expected_size}" ]] \
  || die "AMI root is ${actual_size} GiB; expected exactly ${expected_size} GiB"
[[ "${volume_type}" == "gp3" ]] || die "AMI root volume type is ${volume_type}; expected gp3"
[[ "${encrypted}" == "true" ]] || die "AMI root snapshot is not encrypted"
[[ "${snapshot_id}" =~ ^snap-[0-9a-f]+$ ]] \
  || die "AMI root snapshot ID is invalid: ${snapshot_id}"

snapshot_json="$(
  aws ec2 describe-snapshots \
    --region "${region}" \
    --snapshot-ids "${snapshot_id}" \
    --output json \
    --no-cli-pager
)"
[[ "$(jq -r '.Snapshots[0].VolumeSize' <<<"${snapshot_json}")" == "${expected_size}" ]] \
  || die "root snapshot does not have the expected ${expected_size} GiB volume size"
[[ "$(jq -r '.Snapshots[0].Encrypted' <<<"${snapshot_json}")" == "true" ]] \
  || die "root snapshot is not encrypted"

manifest_tmp="$(mktemp "${MANIFEST}.tmp.XXXXXX")"
trap 'rm -f "${manifest_tmp}"' EXIT
jq \
  --arg role "${ROLE}" \
  --arg ami_id "${ami_id}" \
  --arg parent_ami_id "${PARENT_AMI_ID}" \
  --arg root_snapshot_id "${snapshot_id}" \
  --arg region "${region}" \
  --arg architecture "${architecture}" \
  '
    .flowform_verification = {
      image_role: $role,
      ami_id: $ami_id,
      parent_ami_id: (if $parent_ami_id == "" then null else $parent_ami_id end),
      root_snapshot_id: $root_snapshot_id,
      region: $region,
      architecture: $architecture
    }
  ' "${MANIFEST}" >"${manifest_tmp}"
mv "${manifest_tmp}" "${MANIFEST}"
trap - EXIT

printf 'role=%s\tami=%s\tregion=%s\troot=%s\tsize=%sGiB\ttype=%s\tencrypted=%s\tsnapshot=%s' \
  "${ROLE}" "${ami_id}" "${region}" "${root_device}" "${actual_size}" \
  "${volume_type}" "${encrypted}" "${snapshot_id}"
if [[ -n "${PARENT_AMI_ID}" ]]; then
  printf '\tparent=%s' "${PARENT_AMI_ID}"
fi
printf '\tsource-filter=%s\n' "${source_ami_name}"
