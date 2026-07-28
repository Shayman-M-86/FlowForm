#!/usr/bin/env bash
set -Eeuo pipefail

# Deploy and invoke FlowForm's isolated database-bootstrap Lambda.
#
# DatabaseStack owns only persistent RDS infrastructure. The optional
# DatabaseBootstrapStack owns an idempotent Lambda plus its dedicated security
# groups, but no custom resource and no paid VPC endpoint. This script:
#
#   1. verifies that the persistent database stack is healthy;
#   2. deploys or updates the separate bootstrap helper stack;
#   3. creates one tagged Secrets Manager interface endpoint;
#   4. invokes the bootstrap Lambda and checks its sanitized result; and
#   5. removes the endpoint on success, failure, or interruption.
#
# The helper stack remains deployed for quick retries and future bootstrap
# versions. It has no continuously billed compute. The paid interface endpoint
# exists only while this script is running.
#
# Usage:
#   infra/deployment/aws/scripts/bootstrap-database.sh [--env staging] [--apply]
#   infra/deployment/aws/scripts/bootstrap-database.sh [--env staging] --cleanup
#
# Dry run is the default. Use --apply to deploy and invoke. Use --cleanup to
# remove an endpoint left by an ungraceful workstation or process failure.

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
CDK_DIR="${SCRIPT_DIR}/../cdk"

ENV_NAME="staging"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-southeast-2}}"
APPLY=false
CLEANUP_ONLY=false

ENDPOINT_ID=""
CREATE_ERROR_FILE=""
RESULT_DIR=""

log() { printf '[bootstrap-database] %s\n' "$*"; }
warn() { printf '[bootstrap-database] WARNING: %s\n' "$*" >&2; }
die() {
  printf '[bootstrap-database] ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  sed -n '4,25p' "${BASH_SOURCE[0]}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENV_NAME="${2:?--env needs a value}"
      shift 2
      ;;
    --region)
      REGION="${2:?--region needs a value}"
      shift 2
      ;;
    --apply)
      APPLY=true
      shift
      ;;
    --cleanup)
      CLEANUP_ONLY=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

case "${ENV_NAME}" in
  staging | prod) ;;
  *) die "--env must be staging or prod" ;;
esac

command -v aws >/dev/null || die "aws CLI is required"
command -v jq >/dev/null || die "jq is required"

NAME_SUFFIX="${ENV_NAME^}"
DATABASE_STACK="FlowForm-${NAME_SUFFIX}-Database"
BOOTSTRAP_STACK="FlowForm-${NAME_SUFFIX}-DatabaseBootstrap"

owned_endpoint_ids() {
  aws ec2 describe-vpc-endpoints \
    --region "${REGION}" \
    --filters \
      "Name=tag:ManagedBy,Values=DatabaseBootstrap" \
      "Name=tag:Environment,Values=${ENV_NAME}" \
      "Name=tag:BootstrapStack,Values=${BOOTSTRAP_STACK}" \
      "Name=vpc-endpoint-state,Values=pending,available,pendingAcceptance,rejected,failed,deleting" \
    --query 'VpcEndpoints[].VpcEndpointId' \
    --output text
}

wait_for_endpoint_available() {
  local endpoint_id="$1"
  local endpoint_state

  for _attempt in {1..60}; do
    endpoint_state="$(
      aws ec2 describe-vpc-endpoints \
        --region "${REGION}" \
        --filters "Name=vpc-endpoint-id,Values=${endpoint_id}" \
        --query 'VpcEndpoints[0].State' \
        --output text
    )" || die "could not inspect temporary endpoint ${endpoint_id}"

    case "${endpoint_state}" in
      available)
        log "${endpoint_id} is available"
        return
        ;;
      pending | pendingAcceptance | None)
        sleep 5
        ;;
      deleting | deleted | failed | rejected)
        die "${endpoint_id} entered terminal state ${endpoint_state}"
        ;;
      *)
        die "${endpoint_id} returned unexpected state ${endpoint_state}"
        ;;
    esac
  done

  die "timed out waiting for ${endpoint_id} to become available"
}

remove_endpoint() {
  local endpoint_id="$1"

  log "removing temporary Secrets Manager endpoint ${endpoint_id}"
  if ! aws ec2 delete-vpc-endpoints \
    --region "${REGION}" \
    --vpc-endpoint-ids "${endpoint_id}" \
    --output json >/dev/null; then
    warn "could not request deletion of ${endpoint_id}; run this script with --cleanup"
  else
    for _attempt in {1..60}; do
      endpoint_count="$(
        aws ec2 describe-vpc-endpoints \
          --region "${REGION}" \
          --filters "Name=vpc-endpoint-id,Values=${endpoint_id}" \
          --query 'length(VpcEndpoints)' \
          --output text
      )" || {
        warn "could not confirm deletion of ${endpoint_id}; run this script with --cleanup"
        return
      }
      if [[ "${endpoint_count}" == "0" ]]; then
        log "${endpoint_id} deletion confirmed"
        return
      fi
      sleep 5
    done
    warn "${endpoint_id} is still deleting; run this script with --cleanup later"
  fi
}

cleanup() {
  local exit_code=$?
  trap - EXIT

  if [[ -n "${ENDPOINT_ID}" ]]; then
    remove_endpoint "${ENDPOINT_ID}"
  fi
  if [[ -n "${RESULT_DIR}" ]]; then
    rm -f -- "${RESULT_DIR}/lambda-result.json"
    rmdir -- "${RESULT_DIR}" 2>/dev/null || true
  fi
  if [[ -n "${CREATE_ERROR_FILE}" ]]; then
    rm -f -- "${CREATE_ERROR_FILE}"
  fi

  exit "${exit_code}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ "${CLEANUP_ONLY}" == true ]]; then
  endpoint_ids="$(owned_endpoint_ids)"
  if [[ -z "${endpoint_ids}" || "${endpoint_ids}" == "None" ]]; then
    log "no owned ${ENV_NAME} bootstrap endpoints require cleanup"
    exit 0
  fi

  for endpoint_id in ${endpoint_ids}; do
    remove_endpoint "${endpoint_id}"
  done
  exit 0
fi

database_status="$(
  aws cloudformation describe-stacks \
    --region "${REGION}" \
    --stack-name "${DATABASE_STACK}" \
    --query 'Stacks[0].StackStatus' \
    --output text
)" || die "${DATABASE_STACK} does not exist"

case "${database_status}" in
  CREATE_COMPLETE | UPDATE_COMPLETE | UPDATE_ROLLBACK_COMPLETE) ;;
  *) die "${DATABASE_STACK} must be healthy before bootstrap; current status is ${database_status}" ;;
esac

existing_endpoints="$(owned_endpoint_ids)"
if [[ -n "${existing_endpoints}" && "${existing_endpoints}" != "None" ]]; then
  die "owned bootstrap endpoint already exists (${existing_endpoints}); run with --cleanup first"
fi

log "database stack  ${DATABASE_STACK} (${database_status})"
log "helper stack    ${BOOTSTRAP_STACK}"
log "region          ${REGION}"

if [[ "${APPLY}" != true ]]; then
  log ""
  log "DRY RUN — would deploy the separate helper stack, create one temporary"
  log "Secrets Manager interface endpoint, invoke the idempotent bootstrap,"
  log "verify its sanitized result, and delete the endpoint."
  log ""
  log "re-run with --apply to execute"
  exit 0
fi

command -v npx >/dev/null || die "npx is required"
command -v docker >/dev/null || die "Docker is required to publish the Lambda image asset"

log "deploying the optional bootstrap helper stack"
(
  cd "${CDK_DIR}"
  # Dependencies are intentionally included. The helper adds cross-stack
  # exports to NetworkStack and DatabaseStack on its first deployment.
  npx cdk deploy \
    -c "env=${ENV_NAME}" \
    -c databaseBootstrap=true \
    "${BOOTSTRAP_STACK}"
)

stack_output() {
  local output_key="$1"
  aws cloudformation describe-stacks \
    --region "${REGION}" \
    --stack-name "${BOOTSTRAP_STACK}" \
    --query "Stacks[0].Outputs[?OutputKey=='${output_key}'].OutputValue | [0]" \
    --output text
}

FUNCTION_NAME="$(stack_output BootstrapFunctionName)"
BOOTSTRAP_VERSION="$(stack_output BootstrapVersion)"
BOOTSTRAP_CHECKSUM="$(stack_output BootstrapChecksum)"
VPC_ID="$(stack_output BootstrapVpcId)"
SUBNET_ID="$(stack_output BootstrapSubnetId)"
ENDPOINT_SECURITY_GROUP_ID="$(stack_output BootstrapEndpointSecurityGroupId)"
ENDPOINT_SERVICE_NAME="$(stack_output BootstrapEndpointServiceName)"
LOG_GROUP_NAME="$(stack_output BootstrapLogGroupName)"

for value_name in \
  FUNCTION_NAME \
  BOOTSTRAP_VERSION \
  BOOTSTRAP_CHECKSUM \
  VPC_ID \
  SUBNET_ID \
  ENDPOINT_SECURITY_GROUP_ID \
  ENDPOINT_SERVICE_NAME \
  LOG_GROUP_NAME; do
  [[ -n "${!value_name}" && "${!value_name}" != "None" ]] \
    || die "bootstrap stack output ${value_name} is missing"
done

tag_specification="$(
  jq -cn \
    --arg environment "${ENV_NAME}" \
    --arg stack "${BOOTSTRAP_STACK}" \
    '[
      {
        ResourceType: "vpc-endpoint",
        Tags: [
          {Key: "ManagedBy", Value: "DatabaseBootstrap"},
          {Key: "Environment", Value: $environment},
          {Key: "BootstrapStack", Value: $stack}
        ]
      }
    ]'
)"

log "creating temporary Secrets Manager endpoint"
CREATE_ERROR_FILE="$(mktemp /tmp/flowform-vpc-endpoint-create.XXXXXX)"
for _attempt in {1..30}; do
  if ENDPOINT_ID="$(
    aws ec2 create-vpc-endpoint \
      --region "${REGION}" \
      --vpc-id "${VPC_ID}" \
      --vpc-endpoint-type Interface \
      --service-name "${ENDPOINT_SERVICE_NAME}" \
      --subnet-ids "${SUBNET_ID}" \
      --security-group-ids "${ENDPOINT_SECURITY_GROUP_ID}" \
      --private-dns-enabled \
      --tag-specifications "${tag_specification}" \
      --query 'VpcEndpoint.VpcEndpointId' \
      --output text \
      2>"${CREATE_ERROR_FILE}"
  )"; then
    break
  fi

  if grep -q "already a conflicting DNS domain" "${CREATE_ERROR_FILE}"; then
    log "waiting for the previous endpoint's private DNS association to clear"
    sleep 10
    continue
  fi

  sed 's/^/[aws] /' "${CREATE_ERROR_FILE}" >&2
  die "could not create the temporary Secrets Manager endpoint"
done
[[ -n "${ENDPOINT_ID}" && "${ENDPOINT_ID}" != "None" ]] \
  || {
    sed 's/^/[aws] /' "${CREATE_ERROR_FILE}" >&2
    die "timed out waiting to create the temporary Secrets Manager endpoint"
  }
rm -f -- "${CREATE_ERROR_FILE}"
CREATE_ERROR_FILE=""

log "waiting for ${ENDPOINT_ID} to become available"
wait_for_endpoint_available "${ENDPOINT_ID}"

payload="$(
  jq -cn \
    --arg version "${BOOTSTRAP_VERSION}" \
    --arg checksum "${BOOTSTRAP_CHECKSUM}" \
    '{BootstrapVersion: $version, BootstrapChecksum: $checksum}'
)"
RESULT_DIR="$(mktemp -d /tmp/flowform-database-bootstrap.XXXXXX)"

log "invoking ${FUNCTION_NAME}"
invoke_result="$(
  aws lambda invoke \
    --region "${REGION}" \
    --function-name "${FUNCTION_NAME}" \
    --cli-binary-format raw-in-base64-out \
    --payload "${payload}" \
    "${RESULT_DIR}/lambda-result.json"
)"

if [[ "$(jq -r '.FunctionError // empty' <<<"${invoke_result}")" != "" ]]; then
  die "Lambda invocation failed; inspect ${LOG_GROUP_NAME}"
fi
if ! jq -e \
  --arg version "${BOOTSTRAP_VERSION}" \
  --arg checksum "${BOOTSTRAP_CHECKSUM}" \
  '.Succeeded == true
   and .BootstrapVersion == $version
   and .BootstrapChecksum == $checksum' \
  "${RESULT_DIR}/lambda-result.json" >/dev/null; then
  error_code="$(jq -r '.ErrorCode // "BootstrapFailed"' "${RESULT_DIR}/lambda-result.json")"
  error_message="$(jq -r '.ErrorMessage // "Database bootstrap failed."' "${RESULT_DIR}/lambda-result.json")"
  die "${error_code}: ${error_message} Inspect ${LOG_GROUP_NAME}"
fi

log "database bootstrap ${BOOTSTRAP_VERSION} completed and verified"
