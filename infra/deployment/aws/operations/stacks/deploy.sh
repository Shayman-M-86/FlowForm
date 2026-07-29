#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_lib/common.sh
source "${SCRIPT_DIR}/../_lib/common.sh"

usage() {
  cat <<USAGE
Usage: ${0##*/} --environment <dev|staging|prod> --stack STACK [options] [-- CDK_DEPLOY_ARGS]

Options:
  --diff-only    Run CDK diff without deploying.
  --skip-diff    Deploy without first running CDK diff.
  --exclusively  Do not include stack dependencies in the CDK operation.

Arguments after -- are passed only to cdk deploy.
USAGE
}

environment=""
stack=""
mode="deploy"
run_diff=1
exclusive=0
declare -a deploy_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment)
      [[ $# -ge 2 ]] || operation_die "--environment requires a value"
      environment="$2"
      shift 2
      ;;
    --stack)
      [[ $# -ge 2 ]] || operation_die "--stack requires a value"
      stack="$2"
      shift 2
      ;;
    --diff-only)
      mode="diff"
      shift
      ;;
    --skip-diff)
      run_diff=0
      shift
      ;;
    --exclusively)
      exclusive=1
      shift
      ;;
    --)
      shift
      deploy_args=("$@")
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) operation_die "unknown argument: $1" ;;
  esac
done

[[ -n "${environment}" && -n "${stack}" ]] || { usage >&2; exit 2; }
validate_environment "${environment}"
[[ "${stack}" =~ ^FlowForm-[A-Za-z0-9-]+$ ]] \
  || operation_die "stack must be an exact FlowForm CloudFormation stack name"
[[ -d "${FLOWFORM_CDK_DIR}" ]] || operation_die "CDK directory not found: ${FLOWFORM_CDK_DIR}"
require_command npx

declare -a exclusive_arg=()
if (( exclusive == 1 )); then
  exclusive_arg=(--exclusively)
fi

if [[ "${mode}" == "diff" || "${run_diff}" == "1" ]]; then
  (
    cd -- "${FLOWFORM_CDK_DIR}"
    npx cdk diff -c "env=${environment}" "${exclusive_arg[@]}" "${stack}"
  )
fi

if [[ "${mode}" == "deploy" ]]; then
  (
    cd -- "${FLOWFORM_CDK_DIR}"
    npx cdk deploy -c "env=${environment}" "${exclusive_arg[@]}" "${stack}" "${deploy_args[@]}"
  )
fi

