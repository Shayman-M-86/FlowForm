#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_lib/common.sh
source "${SCRIPT_DIR}/../_lib/common.sh"

usage() {
  cat <<USAGE
Usage: ${0##*/} --environment <staging|prod> --role <app|proxy> [options]

Options:
  --instance-id ID  Bypass Name-tag discovery and target this instance.
  --region REGION   AWS region (default: AWS_REGION or ap-southeast-2).
  --profile PROFILE AWS CLI profile.
  --dry-run         Resolve and validate the target without sending a command.

The role service reloads its complete release manifest and runtime parameters,
then converges the containers without replacing the EC2 instance.
USAGE
}

environment=""
role=""
instance_id=""
region="${AWS_REGION:-ap-southeast-2}"
profile="${AWS_PROFILE:-}"
dry_run=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment)
      [[ $# -ge 2 ]] || operation_die "--environment requires a value"
      environment="$2"
      shift 2
      ;;
    --role)
      [[ $# -ge 2 ]] || operation_die "--role requires a value"
      role="$2"
      shift 2
      ;;
    --instance-id)
      [[ $# -ge 2 ]] || operation_die "--instance-id requires a value"
      instance_id="$2"
      shift 2
      ;;
    --region)
      [[ $# -ge 2 ]] || operation_die "--region requires a value"
      region="$2"
      shift 2
      ;;
    --profile)
      [[ $# -ge 2 ]] || operation_die "--profile requires a value"
      profile="$2"
      shift 2
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) operation_die "unknown argument: $1" ;;
  esac
done

case "${environment}" in
  staging|prod) ;;
  "") usage >&2; exit 2 ;;
  *) operation_die "host convergence is available only for staging or prod" ;;
esac
validate_host_role "${role}"
[[ "${region}" =~ ^[a-z]{2}(-[a-z]+)+-[0-9]+$ ]] || operation_die "invalid AWS region: ${region}"
require_command aws

declare -a aws_args=(--region "${region}" --no-cli-pager)
if [[ -n "${profile}" ]]; then
  aws_args+=(--profile "${profile}")
fi

if [[ -z "${instance_id}" ]]; then
  instance_text="$(
    aws ec2 describe-instances \
      "${aws_args[@]}" \
      --filters \
        "Name=tag:Name,Values=flowform-${environment}-${role}" \
        "Name=instance-state-name,Values=running" \
      --query 'Reservations[].Instances[].InstanceId' \
      --output text
  )"
  read -r -a instances <<<"${instance_text}"
  [[ ${#instances[@]} -eq 1 ]] \
    || operation_die "expected one running flowform-${environment}-${role} instance; found ${#instances[@]}"
  instance_id="${instances[0]}"
fi
[[ "${instance_id}" =~ ^i-[0-9a-f]+$ ]] || operation_die "invalid EC2 instance ID: ${instance_id}"

ping_status="$(
  aws ssm describe-instance-information \
    "${aws_args[@]}" \
    --filters "Key=InstanceIds,Values=${instance_id}" \
    --query 'InstanceInformationList[0].PingStatus' \
    --output text
)"
[[ "${ping_status}" == "Online" ]] \
  || operation_die "instance ${instance_id} is not online in Systems Manager (status: ${ping_status})"

printf 'target environment=%s role=%s instance=%s region=%s\n' \
  "${environment}" "${role}" "${instance_id}" "${region}"
if (( dry_run == 1 )); then
  printf 'DRY_RUN: would restart flowform-%s.service through SSM Run Command\n' "${role}"
  exit 0
fi

commands="$(
  printf '["sudo systemctl restart flowform-%s.service","sudo systemctl is-active --quiet flowform-%s.service"]' \
    "${role}" "${role}"
)"
command_id="$(
  aws ssm send-command \
    "${aws_args[@]}" \
    --instance-ids "${instance_id}" \
    --document-name AWS-RunShellScript \
    --comment "Converge FlowForm ${environment} ${role} release" \
    --parameters "commands=${commands}" \
    --query 'Command.CommandId' \
    --output text
)"

wait_status=0
aws ssm wait command-executed \
  "${aws_args[@]}" \
  --command-id "${command_id}" \
  --instance-id "${instance_id}" \
  || wait_status=$?
aws ssm get-command-invocation \
  "${aws_args[@]}" \
  --command-id "${command_id}" \
  --instance-id "${instance_id}" \
  --query '{Status:Status,Output:StandardOutputContent,Error:StandardErrorContent}' \
  --output json
[[ ${wait_status} -eq 0 ]] \
  || operation_die "SSM convergence command ${command_id} did not succeed"
