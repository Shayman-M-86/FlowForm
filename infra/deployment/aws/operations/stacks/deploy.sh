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

operation_init "cdk-${mode}-${stack}" "${environment}"
operation_install_exit_trap

diff_transcript=""
deploy_transcript=""
outputs_file=""
failure_events=""
operation_status=0
operation_set_summary_metadata \
  stack "${stack}" \
  mode "${mode}" \
  diff_transcript "${diff_transcript}" \
  deploy_transcript "${deploy_transcript}" \
  outputs_file "${outputs_file}" \
  failure_events "${failure_events}"

[[ -d "${FLOWFORM_CDK_DIR}" ]] || operation_die "CDK directory not found: ${FLOWFORM_CDK_DIR}"
require_command npx

declare -a exclusive_arg=()
if (( exclusive == 1 )); then
  exclusive_arg=(--exclusively)
fi

run_logged_in_cdk_dir() {
  local transcript="$1"
  shift

  (
    cd -- "${FLOWFORM_CDK_DIR}"
    operation_run_logged "${transcript}" "$@"
  )
}

collect_failure_events() {
  failure_events="${FLOWFORM_OPERATION_ARTIFACT_DIR}/cloudformation-events.log"
  operation_set_summary_metadata failure_events "${failure_events}"
  if ! command -v aws >/dev/null 2>&1; then
    operation_log "warning" \
      "AWS CLI unavailable; CloudFormation failure events were not collected"
    failure_events=""
    operation_set_summary_metadata failure_events "${failure_events}"
    return
  fi

  operation_log "phase" \
    "retrieving recent CloudFormation events for stack=${stack}"
  if run_logged_in_cdk_dir \
    "${failure_events}" \
    aws cloudformation describe-stack-events \
      --stack-name "${stack}" \
      --max-items 50 \
      --output table; then
    operation_log "info" "CloudFormation events=${failure_events}"
  else
    operation_log "warning" \
      "CloudFormation event retrieval failed; diagnostic output=${failure_events}"
  fi
}

if [[ "${mode}" == "diff" || "${run_diff}" == "1" ]]; then
  diff_transcript="${FLOWFORM_OPERATION_ARTIFACT_DIR}/cdk-diff.log"
  operation_set_summary_metadata diff_transcript "${diff_transcript}"
  operation_log "phase" "running CDK diff for stack=${stack}"
  if run_logged_in_cdk_dir \
    "${diff_transcript}" \
    npx cdk diff -c "env=${environment}" "${exclusive_arg[@]}" "${stack}"; then
    operation_log "info" "CDK diff completed; transcript=${diff_transcript}"
  else
    operation_status=$?
    operation_log "error" \
      "CDK diff failed with exit_code=${operation_status}; transcript=${diff_transcript}"
  fi
fi

if (( operation_status == 0 )) && [[ "${mode}" == "deploy" ]]; then
  deploy_transcript="${FLOWFORM_OPERATION_ARTIFACT_DIR}/cdk-deploy.log"
  outputs_file="${FLOWFORM_OPERATION_ARTIFACT_DIR}/stack-outputs.json"
  operation_set_summary_metadata \
    deploy_transcript "${deploy_transcript}" \
    outputs_file "${outputs_file}"
  printf '{}\n' > "${outputs_file}"
  chmod 600 "${outputs_file}"

  operation_log "phase" "deploying CDK stack=${stack}"
  if run_logged_in_cdk_dir \
    "${deploy_transcript}" \
    npx cdk deploy -c "env=${environment}" "${exclusive_arg[@]}" \
      "${stack}" "${deploy_args[@]}" --outputs-file "${outputs_file}"; then
    operation_log "info" "CDK deployment completed; transcript=${deploy_transcript}"
    operation_log "info" "stack outputs=${outputs_file}"
  else
    operation_status=$?
    operation_log "error" \
      "CDK deployment failed with exit_code=${operation_status}; transcript=${deploy_transcript}"
  fi
fi

if (( operation_status != 0 )); then
  collect_failure_events
fi

operation_finish "${operation_status}"
exit "${operation_status}"
