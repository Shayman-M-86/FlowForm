#!/usr/bin/env bash
set -Eeuo pipefail

# Boot-time seed for the isolated rehearsal LocalStack. Runs INSIDE the fixtures
# VM (230) after LocalStack becomes healthy, from Terraform-supplied NON-SECRET
# values only.
#
# SECRET-FREE BY DESIGN. This script no longer creates any Secrets Manager entry
# and no longer consumes any secret value. It establishes exactly what can be
# known without a secret:
#   * the rehearsal KMS key (+ alias), and
#   * every non-secret SSM parameter the runtime reads.
#
# The four Secrets Manager entries (app-secrets, db-secrets, linkage-secret,
# observability-secrets) and the two SSM parameters that depend on the linkage
# secret's ARN (scope + backend linkage_secret_arn) are written LATER by the
# deploy-time SSH synchronisation step (`rehearsal sync` on the operator
# workstation → sync-secrets-into-localstack.sh on this VM). Rebuilding this VM
# therefore comes up with no secrets until that step runs — fail-closed by
# construction. All operations here are create-or-update and safe to rerun.

: "${FLOWFORM_SCOPE:=nonprod}"
: "${AWS_REGION:=ap-southeast-2}"
# Seeds run ON the fixtures VM; LocalStack is bound to loopback (no off-box port).
LS_ENDPOINT="${AWS_ENDPOINT_URL:-http://127.0.0.1:4566}"
CONTRACT="${RUNTIME_PARAMETER_CONTRACT:-/opt/flowform/localstack/runtime-parameter-contract.json}"
HEALTH_ATTEMPTS="${LOCALSTACK_HEALTH_ATTEMPTS:-60}"
HEALTH_DELAY_SECONDS="${LOCALSTACK_HEALTH_DELAY_SECONDS:-2}"

AWS=(aws --endpoint-url "${LS_ENDPOINT}" --region "${AWS_REGION}")
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"

log() { printf '[seed-localstack] %s\n' "$*"; }
die() { printf '[seed-localstack] ERROR: %s\n' "$*" >&2; exit 1; }

command -v aws >/dev/null 2>&1 || die "aws CLI is required"
command -v curl >/dev/null 2>&1 || die "curl is required"
command -v jq >/dev/null 2>&1 || die "jq is required"
[[ -f "${CONTRACT}" ]] || die "runtime parameter contract not found: ${CONTRACT}"
jq -e '.schema_version == 1' "${CONTRACT}" >/dev/null \
  || die "unsupported or invalid runtime parameter contract: ${CONTRACT}"

wait_for_localstack() {
  local attempt
  for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
    if curl -fsS --max-time 5 "${LS_ENDPOINT}/_localstack/health" >/dev/null 2>&1; then
      log "LocalStack healthy at ${LS_ENDPOINT}"
      return
    fi
    if ((attempt == 1 || attempt % 10 == 0)); then
      log "waiting for LocalStack health (${attempt}/${HEALTH_ATTEMPTS})"
    fi
    sleep "${HEALTH_DELAY_SECONDS}"
  done
  die "LocalStack did not become healthy at ${LS_ENDPOINT}"
}

contract_value() {
  local expression="$1"
  jq -er "${expression}" "${CONTRACT}" \
    || die "missing contract value: ${expression}"
}

scope_parameter_name() {
  local logical_name="$1" suffix
  suffix="$(contract_value ".scope_parameters.${logical_name}")"
  printf '/flowform/%s/%s' "${FLOWFORM_SCOPE}" "${suffix}"
}

runtime_parameter_name() {
  local group="$1" logical_name="$2" path name
  path="$(contract_value ".runtime_groups.${group}.path")"
  name="$(contract_value ".runtime_groups.${group}.parameters.${logical_name}.name")"
  printf '/flowform/%s/%s/%s' "${FLOWFORM_SCOPE}" "${path}" "${name}"
}

validate_seed_environment() {
  local key
  # Only NON-SECRET runtime-parameter seed keys remain (secret_seed_value_keys is
  # empty). Each must be present in the environment or the seed writes empties.
  while IFS= read -r key; do
    [[ -n "${key}" ]] || continue
    [[ -n "${!key:-}" ]] || die "required Terraform seed value is unset: ${key}"
  done < <(jq -r '(.runtime_groups[].parameters[].seed_value_key // empty),
                  (.secret_seed_value_keys[]? // empty)' "${CONTRACT}" | sort -u)
}

put_parameter() {
  local name="$1" value="$2" type="${3:-String}"
  "${AWS[@]}" ssm put-parameter --name "${name}" --value "${value}" \
    --type "${type}" --overwrite --query Version --output text >/dev/null
  log "put parameter ${name} (${type})"
}

put_runtime_parameter() {
  local group="$1" logical_name="$2" value="$3"
  put_parameter "$(runtime_parameter_name "${group}" "${logical_name}")" "${value}"
}

ensure_kms_key() {
  local alias_name="alias/flowform-${FLOWFORM_SCOPE}-rehearsal" key_arn key_id
  if key_arn="$("${AWS[@]}" kms describe-key --key-id "${alias_name}" \
    --query KeyMetadata.Arn --output text 2>/dev/null)"; then
    printf '%s' "${key_arn}"
    return
  fi

  key_id="$("${AWS[@]}" kms create-key \
    --description "FlowForm ${FLOWFORM_SCOPE} rehearsal key" \
    --query KeyMetadata.KeyId --output text)"
  "${AWS[@]}" kms create-alias --alias-name "${alias_name}" --target-key-id "${key_id}"
  "${AWS[@]}" kms describe-key --key-id "${key_id}" --query KeyMetadata.Arn --output text
}

main() {
  wait_for_localstack
  validate_seed_environment
  log "scope=${FLOWFORM_SCOPE} contract=${CONTRACT} (secret-free boot seed)"

  local kms_key_arn
  kms_key_arn="$(ensure_kms_key)"

  # Scope-level identifiers. linkage_secret_arn is NOT written here — it depends
  # on the linkage secret, which the deploy-time sync creates and whose ARN it
  # then records into both the scope and backend parameters.
  put_parameter "$(scope_parameter_name kms_key_arn)" "${kms_key_arn}"
  put_parameter "$(scope_parameter_name aws_region)" "${AWS_REGION}"

  put_runtime_parameter backend logging_json "${FLOWFORM_LOGGING_LOG_JSON}"
  put_runtime_parameter backend logging_level "${FLOWFORM_LOGGING_LEVEL}"
  put_runtime_parameter backend runtime_environment "${FLOWFORM_ENV}"
  put_runtime_parameter backend backend_image "${BACKEND_IMAGE}"
  put_runtime_parameter backend auth0_domain "${FLOWFORM_AUTH0_DOMAIN}"
  put_runtime_parameter backend auth0_management_domain "${FLOWFORM_AUTH0_MGMT_DOMAIN}"
  put_runtime_parameter backend auth0_audience "${FLOWFORM_AUTH0_AUDIENCE}"
  put_runtime_parameter backend auth0_client_id "${FLOWFORM_AUTH0_CLIENT_ID}"
  put_runtime_parameter backend auth0_management_id "${FLOWFORM_AUTH0_MGMT_ID}"
  put_runtime_parameter backend auth0_management_validate_on_startup "${FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP}"
  put_runtime_parameter backend aws_region "${AWS_REGION}"
  put_runtime_parameter backend email_from_address "${FLOWFORM_EMAIL_FROM_ADDRESS}"
  put_runtime_parameter backend kms_key_arn "${kms_key_arn}"
  put_runtime_parameter backend database_core_host "${DATABASE_CORE_HOST}"
  put_runtime_parameter backend database_core_name "${DATABASE_CORE_NAME}"
  put_runtime_parameter backend database_core_app_user "${DATABASE_CORE_APP_USER}"
  put_runtime_parameter backend database_response_host "${DATABASE_RESPONSE_HOST}"
  put_runtime_parameter backend database_response_name "${DATABASE_RESPONSE_NAME}"
  put_runtime_parameter backend database_response_app_user "${DATABASE_RESPONSE_APP_USER}"

  put_runtime_parameter proxy caddy_image "${CADDY_IMAGE}"
  put_runtime_parameter proxy api_domain "${API_DOMAIN}"
  put_runtime_parameter proxy grafana_cloud_loki_url "${GRAFANA_CLOUD_LOKI_URL}"
  put_runtime_parameter proxy grafana_cloud_loki_user "${GRAFANA_CLOUD_LOKI_USER}"

  log "boot seed complete for /flowform/${FLOWFORM_SCOPE} (KMS + non-secret SSM only)"
}

main "$@"
