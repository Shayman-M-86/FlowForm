#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'USAGE'
Usage: publish-aws-ami.sh SSM_PARAMETER_NAME [AWS_REGION]

Publish the most recent amazon-ebs AMI ID from the Packer manifest to an
explicit SSM parameter. Building the AMI remains the responsibility of
build-aws-image.sh.
USAGE
}

[[ $# -ge 1 && $# -le 2 ]] || { usage >&2; exit 2; }
command -v aws >/dev/null 2>&1 || { echo 'aws command not found' >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo 'jq command not found' >&2; exit 1; }

parameter_name="$1"
region="${2:-}"
ami_id="$(${SCRIPT_DIR}/extract-aws-ami-id.sh)"
[[ "${ami_id}" =~ ^ami-[0-9a-f]+$ ]] || {
  printf 'Invalid AMI ID in Packer manifest: %s\n' "${ami_id}" >&2
  exit 1
}

aws_args=(ssm put-parameter --name "${parameter_name}" --type String --value "${ami_id}" --overwrite)
[[ -z "${region}" ]] || aws_args+=(--region "${region}")
aws "${aws_args[@]}"
