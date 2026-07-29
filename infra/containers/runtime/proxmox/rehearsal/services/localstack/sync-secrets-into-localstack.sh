#!/usr/bin/env bash
set -Eeuo pipefail

# Deploy-time secret synchroniser — the VM-230 side.
#
# Reads an allow-listed tar archive from STDIN (streamed over SSH by the operator
# workstation's `rehearsal sync` command), stages it under a private tmpfs in
# /run, validates every member's NAME and MODE, and reconciles the four rehearsal
# Secrets Manager entries into the loopback LocalStack. Secret values are handed
# to the AWS CLI exclusively through protected `file://` inputs — never on argv —
# so no secret ever appears in a process listing or an argv-logging shim.
#
# Idempotent and self-healing:
#   * Each entry is compared against the current LocalStack value; identical
#     values are skipped, so reruns mint no new secret versions.
#   * The linkage secret is APPEND-ONLY and version-stable: each historical
#     version carries the UUID ClientRequestToken supplied in the archive, so
#     rebuilding this VM recreates the SAME Secrets Manager version IDs.
#   * A partial failure (some entries written, then an error) is safely repaired
#     by rerunning: already-current entries are skipped, missing ones created.
#
# After the secret entries are in place it records the linkage secret's ARN into
# the scope + backend linkage_secret_arn SSM parameters (the boot seed leaves
# these unwritten because they depend on the linkage secret existing).
#
# The archive is the ONLY secret channel. This script takes no secret arguments
# and prints no secret values.

: "${FLOWFORM_SCOPE:=nonprod}"
: "${AWS_REGION:=ap-southeast-2}"
LS_ENDPOINT="${AWS_ENDPOINT_URL:-http://127.0.0.1:4566}"
CONTRACT="${RUNTIME_PARAMETER_CONTRACT:-/opt/flowform/localstack/runtime-parameter-contract.json}"
HEALTH_ATTEMPTS="${LOCALSTACK_HEALTH_ATTEMPTS:-90}"
HEALTH_DELAY_SECONDS="${LOCALSTACK_HEALTH_DELAY_SECONDS:-2}"

AWS=(aws --endpoint-url "${LS_ENDPOINT}" --region "${AWS_REGION}")
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"

log() { printf '[sync-secrets] %s\n' "$*"; }
die() { printf '[sync-secrets] ERROR: %s\n' "$*" >&2; exit 1; }

command -v aws >/dev/null 2>&1 || die "aws CLI is required"
command -v curl >/dev/null 2>&1 || die "curl is required"
command -v jq >/dev/null 2>&1 || die "jq is required"
command -v tar >/dev/null 2>&1 || die "tar is required"
[[ -f "${CONTRACT}" ]] || die "runtime parameter contract not found: ${CONTRACT}"

# The exact set of archive members allowed. Anything else is rejected — the
# archive cannot smuggle a path traversal, a symlink, or an unexpected file.
ALLOWED_SECRET_FILES=(app-secrets.json db-secrets.json linkage-secret.json observability-secrets.json)
ALLOWED_META_FILES=(meta.json linkage-client-request-token)

STAGE=""
cleanup() { [[ -n "${STAGE}" && -d "${STAGE}" ]] && rm -rf "${STAGE}"; STAGE=""; }
trap cleanup EXIT INT TERM HUP

wait_for_localstack() {
  local attempt
  for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
    if curl -fsS --max-time 5 "${LS_ENDPOINT}/_localstack/health" >/dev/null 2>&1; then
      log "LocalStack healthy at ${LS_ENDPOINT}"
      return 0
    fi
    if ((attempt == 1 || attempt % 10 == 0)); then
      log "waiting for LocalStack health (${attempt}/${HEALTH_ATTEMPTS})"
    fi
    sleep "${HEALTH_DELAY_SECONDS}"
  done
  die "LocalStack did not become healthy at ${LS_ENDPOINT}; inspect flowform-localstack container and service logs"
}

secret_name() {
  local logical_name="$1" suffix
  suffix="$(jq -er ".secrets.${logical_name}" "${CONTRACT}")" \
    || die "contract has no secret mapping for ${logical_name}"
  printf 'flowform/%s/%s' "${FLOWFORM_SCOPE}" "${suffix}"
}

scope_parameter_name() {
  local logical_name="$1" suffix
  suffix="$(jq -er ".scope_parameters.${logical_name}" "${CONTRACT}")" \
    || die "contract has no scope parameter ${logical_name}"
  printf '/flowform/%s/%s' "${FLOWFORM_SCOPE}" "${suffix}"
}

runtime_parameter_name() {
  local group="$1" logical_name="$2" path name
  path="$(jq -er ".runtime_groups.${group}.path" "${CONTRACT}")" || die "bad group ${group}"
  name="$(jq -er ".runtime_groups.${group}.parameters.${logical_name}.name" "${CONTRACT}")" \
    || die "bad parameter ${group}.${logical_name}"
  printf '/flowform/%s/%s/%s' "${FLOWFORM_SCOPE}" "${path}" "${name}"
}

# Stage the stdin archive into a private tmpfs directory and validate it.
stage_archive() {
  STAGE="$(mktemp -d /run/flowform-sync.XXXXXX)" \
    || die "could not create staging dir under /run (tmpfs required)"
  chmod 0700 "${STAGE}"

  # Refuse anything but plain files: no absolute paths, no '..', no symlinks,
  # no devices. tar's own extraction is constrained, and we re-validate below.
  if ! tar -xf - -C "${STAGE}" 2>/dev/null; then
    die "failed to extract the secret archive from stdin"
  fi

  # Every extracted entry must be a regular file in the allow-list, mode 0600.
  local allowed=" ${ALLOWED_SECRET_FILES[*]} ${ALLOWED_META_FILES[*]} "
  local found
  while IFS= read -r -d '' found; do
    local rel="${found#"${STAGE}/"}"
    [[ "${rel}" == "${found}" ]] && continue # skip the staging dir itself
    [[ -f "${found}" && ! -L "${found}" ]] \
      || die "archive member is not a regular file: ${rel}"
    [[ "${allowed}" == *" ${rel} "* ]] \
      || die "archive contains a non-allow-listed member: ${rel}"
    local mode
    mode="$(stat -c '%a' "${found}")"
    [[ "${mode}" == "600" ]] \
      || die "archive member ${rel} has mode ${mode}, expected 600"
  done < <(find "${STAGE}" -mindepth 1 -print0)

  # The four secret payloads and the linkage token are mandatory; meta optional.
  local required
  for required in "${ALLOWED_SECRET_FILES[@]}" linkage-client-request-token; do
    [[ -f "${STAGE}/${required}" ]] || die "archive is missing required member: ${required}"
  done

  # Payloads must be valid single JSON objects (linkage token is a bare UUID).
  local f
  for f in "${ALLOWED_SECRET_FILES[@]}"; do
    jq -e 'type == "object"' "${STAGE}/${f}" >/dev/null 2>&1 \
      || die "archive member ${f} is not a JSON object"
  done
  grep -Eqx '[0-9a-fA-F-]{36}' "${STAGE}/linkage-client-request-token" \
    || die "linkage-client-request-token is not a UUID"

  log "staged and validated ${#ALLOWED_SECRET_FILES[@]} secret payloads under ${STAGE}"
}

# Current SecretString for a secret id, or empty string if it does not exist.
current_secret_string() {
  local secret_id="$1"
  "${AWS[@]}" secretsmanager get-secret-value --secret-id "${secret_id}" \
    --query SecretString --output text 2>/dev/null || printf ''
}

# Create-or-update a plain (non-versioned-history) secret from a staged file,
# skipping the write when the current value already matches. file:// keeps the
# value off argv.
reconcile_plain_secret() {
  local logical="$1" file="$2" secret_id current desired
  secret_id="$(secret_name "${logical}")"
  desired="$(cat "${file}")"
  current="$(current_secret_string "${secret_id}")"
  if [[ "${current}" == "${desired}" ]]; then
    log "secret ${secret_id} already current — no new version"
    return
  fi
  if "${AWS[@]}" secretsmanager describe-secret --secret-id "${secret_id}" >/dev/null 2>&1; then
    "${AWS[@]}" secretsmanager put-secret-value --secret-id "${secret_id}" \
      --secret-string "file://${file}" --query VersionId --output text >/dev/null
    log "updated secret ${secret_id}"
  else
    "${AWS[@]}" secretsmanager create-secret --name "${secret_id}" \
      --secret-string "file://${file}" --query ARN --output text >/dev/null
    log "created secret ${secret_id}"
  fi
}

# Reconcile the append-only linkage secret. The archive's linkage-secret.json is
# the CURRENT desired version; the ClientRequestToken makes the version id stable
# across VM rebuilds. If the current value already matches, do nothing.
reconcile_linkage_secret() {
  local file="$1" token_file="$2" secret_id current desired token
  secret_id="$(secret_name linkage)"
  desired="$(cat "${file}")"
  token="$(cat "${token_file}")"
  current="$(current_secret_string "${secret_id}")"
  if [[ "${current}" == "${desired}" ]]; then
    log "linkage secret ${secret_id} already current — no new version"
    return
  fi
  if "${AWS[@]}" secretsmanager describe-secret --secret-id "${secret_id}" >/dev/null 2>&1; then
    # Append a new historical version under its stable token. A rerun with the
    # same token+value is idempotent in Secrets Manager (returns the existing
    # version) — safe partial-failure recovery.
    "${AWS[@]}" secretsmanager put-secret-value --secret-id "${secret_id}" \
      --secret-string "file://${file}" \
      --client-request-token "${token}" \
      --query VersionId --output text >/dev/null
    log "appended linkage secret version to ${secret_id} (stable token)"
  else
    "${AWS[@]}" secretsmanager create-secret --name "${secret_id}" \
      --secret-string "file://${file}" \
      --client-request-token "${token}" \
      --query ARN --output text >/dev/null
    log "created linkage secret ${secret_id} (stable token)"
  fi
}

record_linkage_arn() {
  local secret_id arn
  secret_id="$(secret_name linkage)"
  arn="$("${AWS[@]}" secretsmanager describe-secret --secret-id "${secret_id}" \
    --query ARN --output text)" || die "could not read linkage secret ARN"
  "${AWS[@]}" ssm put-parameter --name "$(scope_parameter_name linkage_secret_arn)" \
    --value "${arn}" --type String --overwrite --query Version --output text >/dev/null
  "${AWS[@]}" ssm put-parameter --name "$(runtime_parameter_name backend linkage_secret_arn)" \
    --value "${arn}" --type String --overwrite --query Version --output text >/dev/null
  log "recorded linkage secret ARN into scope + backend SSM parameters"
}

main() {
  wait_for_localstack
  stage_archive
  reconcile_plain_secret app "${STAGE}/app-secrets.json"
  reconcile_plain_secret database "${STAGE}/db-secrets.json"
  reconcile_plain_secret observability "${STAGE}/observability-secrets.json"
  reconcile_linkage_secret "${STAGE}/linkage-secret.json" "${STAGE}/linkage-client-request-token"
  record_linkage_arn
  cleanup
  log "secret synchronisation complete for /flowform/${FLOWFORM_SCOPE}"
}

main "$@"
