#!/usr/bin/env bash

OPERATIONS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_DEPLOYMENT_DIR="$(cd -- "${OPERATIONS_DIR}/.." && pwd)"
REPO_ROOT="$(cd -- "${AWS_DEPLOYMENT_DIR}/../../.." && pwd)"

FLOWFORM_IMAGE_TOOL="${FLOWFORM_IMAGE_TOOL:-${REPO_ROOT}/infra/machine-images/tooling/image}"
FLOWFORM_CONTAINER_PUBLISHER="${FLOWFORM_CONTAINER_PUBLISHER:-${AWS_DEPLOYMENT_DIR}/scripts/publish-staging-images.sh}"
FLOWFORM_CDK_DIR="${FLOWFORM_CDK_DIR:-${AWS_DEPLOYMENT_DIR}/cdk}"
FLOWFORM_OPERATION_ARTIFACT_ROOT="${FLOWFORM_OPERATION_ARTIFACT_ROOT:-${TMPDIR:-/tmp}/flowform-operation-artifacts}"
declare -gA FLOWFORM_OPERATION_SUMMARY_METADATA=()

operation_timestamp() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

operation_json_escape() {
  local value="$1"

  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  value="${value//$'\t'/\\t}"
  printf '%s' "${value}"
}

operation_slug() {
  local value="$1"

  value="${value//[^A-Za-z0-9._-]/-}"
  value="${value#-}"
  value="${value%-}"
  [[ -n "${value}" ]] || value="operation"
  printf '%s' "${value:0:128}"
}

operation_log() {
  local level="${1^^}"
  shift
  local message="$*"
  local timestamp

  timestamp="$(operation_timestamp)"
  printf '%s | %-7s | %-28s | %s\n' \
    "${timestamp}" \
    "${level}" \
    "${FLOWFORM_OPERATION_NAME:-aws-operation}" \
    "${message}"

  if [[ -n "${FLOWFORM_OPERATION_ARTIFACT_DIR:-}" ]]; then
    {
      printf '{"timestamp":"%s","level":"%s","environment":"%s",' \
        "$(operation_json_escape "${timestamp}")" \
        "$(operation_json_escape "${level,,}")" \
        "$(operation_json_escape "${FLOWFORM_OPERATION_ENVIRONMENT:-unknown}")"
      printf '"operation_id":"%s","operation":"%s","source_commit":"%s","component":"aws-operations","message":"%s"}\n' \
        "$(operation_json_escape "${FLOWFORM_OPERATION_ID:-unknown}")" \
        "$(operation_json_escape "${FLOWFORM_OPERATION_NAME:-aws-operation}")" \
        "$(operation_json_escape "${FLOWFORM_OPERATION_SOURCE_COMMIT:-unknown}")" \
        "$(operation_json_escape "${message}")"
    } >> "${FLOWFORM_OPERATION_ARTIFACT_DIR}/operation.jsonl"
    chmod 600 "${FLOWFORM_OPERATION_ARTIFACT_DIR}/operation.jsonl"
  fi
}

operation_set_summary_metadata() {
  local key
  local value

  (( $# % 2 == 0 )) \
    || operation_die "operation summary metadata must be key/value pairs"
  while (( $# > 0 )); do
    key="$1"
    value="$2"
    shift 2
    [[ "${key}" =~ ^[a-z][a-z0-9_]*$ ]] \
      || operation_die "invalid operation summary key: ${key}"
    FLOWFORM_OPERATION_SUMMARY_METADATA["${key}"]="${value}"
  done
}

operation_init() {
  local operation_name="$1"
  local environment="$2"
  local operation_slug_value
  local generated_suffix

  [[ -n "${operation_name}" ]] || operation_die "operation name is required"
  case "${environment}" in
    dev|staging|prod|shared) ;;
    *) operation_die "operation environment must be dev, staging, prod, or shared" ;;
  esac

  FLOWFORM_OPERATION_NAME="${operation_name}"
  FLOWFORM_OPERATION_ENVIRONMENT="${environment}"
  FLOWFORM_OPERATION_STARTED_AT="$(operation_timestamp)"
  FLOWFORM_OPERATION_STARTED_EPOCH="$(date -u '+%s')"
  if [[ -z "${FLOWFORM_OPERATION_SOURCE_COMMIT:-}" ]]; then
    FLOWFORM_OPERATION_SOURCE_COMMIT="$(
      git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null || printf 'unknown'
    )"
  fi

  if [[ -z "${FLOWFORM_OPERATION_ID:-}" ]]; then
    if [[ -r /proc/sys/kernel/random/uuid ]]; then
      read -r generated_suffix < /proc/sys/kernel/random/uuid
    else
      generated_suffix="${RANDOM}${RANDOM}"
    fi
    FLOWFORM_OPERATION_ID="$(
      operation_slug \
        "${environment}-${operation_name}-${FLOWFORM_OPERATION_STARTED_AT//[:T-]/}-${FLOWFORM_OPERATION_SOURCE_COMMIT:0:8}-${generated_suffix:0:8}"
    )"
  fi
  [[ "${FLOWFORM_OPERATION_ID}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] \
    || operation_die "FLOWFORM_OPERATION_ID must contain only letters, digits, dots, underscores, or hyphens"

  operation_slug_value="$(operation_slug "${operation_name}")"
  FLOWFORM_OPERATION_ARTIFACT_DIR="${FLOWFORM_OPERATION_ARTIFACT_ROOT}/${FLOWFORM_OPERATION_ID}/${operation_slug_value}"
  FLOWFORM_OPERATION_FINISHED=0
  FLOWFORM_OPERATION_FINISHING=0
  FLOWFORM_OPERATION_SUMMARY_METADATA=()

  umask 077
  mkdir -p -- "${FLOWFORM_OPERATION_ARTIFACT_DIR}"
  chmod 700 \
    "${FLOWFORM_OPERATION_ARTIFACT_ROOT}/${FLOWFORM_OPERATION_ID}" \
    "${FLOWFORM_OPERATION_ARTIFACT_DIR}"

  export \
    FLOWFORM_OPERATION_ARTIFACT_DIR \
    FLOWFORM_OPERATION_ARTIFACT_ROOT \
    FLOWFORM_OPERATION_ENVIRONMENT \
    FLOWFORM_OPERATION_ID \
    FLOWFORM_OPERATION_NAME \
    FLOWFORM_OPERATION_SOURCE_COMMIT \
    FLOWFORM_OPERATION_STARTED_AT

  : > "${FLOWFORM_OPERATION_ARTIFACT_DIR}/operation.jsonl"
  chmod 600 "${FLOWFORM_OPERATION_ARTIFACT_DIR}/operation.jsonl"
  operation_log "phase" \
    "started operation_id=${FLOWFORM_OPERATION_ID} environment=${environment} source_commit=${FLOWFORM_OPERATION_SOURCE_COMMIT}"
  operation_log "info" "artifacts=${FLOWFORM_OPERATION_ARTIFACT_DIR}"
}

_operation_handle_exit() {
  local exit_code="$1"

  trap - EXIT INT TERM
  if [[ -n "${FLOWFORM_OPERATION_ARTIFACT_DIR:-}" ]] \
    && [[ "${FLOWFORM_OPERATION_FINISHED:-0}" != "1" ]] \
    && [[ "${FLOWFORM_OPERATION_FINISHING:-0}" != "1" ]]; then
    operation_finish "${exit_code}"
  fi
  exit "${exit_code}"
}

_operation_handle_signal() {
  local exit_code="$1"

  trap - INT TERM
  exit "${exit_code}"
}

operation_install_exit_trap() {
  trap '_operation_handle_exit "$?"' EXIT
  trap '_operation_handle_signal 130' INT
  trap '_operation_handle_signal 143' TERM
}

operation_run_logged() {
  local transcript="$1"
  shift
  local had_errexit=0
  local command_status
  local -a pipeline_statuses=()

  [[ -n "${transcript}" ]] || operation_die "operation transcript path is required"
  mkdir -p -- "$(dirname -- "${transcript}")"
  : > "${transcript}"
  chmod 600 "${transcript}"

  [[ $- == *e* ]] && had_errexit=1
  set +e
  "$@" 2>&1 | tee "${transcript}"
  pipeline_statuses=("${PIPESTATUS[@]}")
  (( had_errexit == 1 )) && set -e

  command_status="${pipeline_statuses[0]}"
  if (( ${pipeline_statuses[1]:-0} != 0 )); then
    operation_log "warning" "could not write the complete transcript: ${transcript}"
  fi
  return "${command_status}"
}

operation_finish() {
  local exit_code="$1"
  shift
  local finished_at
  local finished_epoch
  local duration_seconds
  local outcome
  local summary_path
  local temporary_summary
  local key
  local value
  local -a metadata_keys=()

  [[ -n "${FLOWFORM_OPERATION_ARTIFACT_DIR:-}" ]] \
    || operation_die "operation_finish called before operation_init"
  if [[ "${FLOWFORM_OPERATION_FINISHED:-0}" == "1" ]]; then
    return
  fi
  [[ "${exit_code}" =~ ^[0-9]+$ ]] \
    || operation_die "operation exit code must be a non-negative integer"
  operation_set_summary_metadata "$@"
  FLOWFORM_OPERATION_FINISHING=1

  finished_at="$(operation_timestamp)"
  finished_epoch="$(date -u '+%s')"
  duration_seconds="$((finished_epoch - FLOWFORM_OPERATION_STARTED_EPOCH))"
  if (( exit_code == 0 )); then
    outcome="success"
  else
    outcome="failure"
  fi

  summary_path="${FLOWFORM_OPERATION_ARTIFACT_DIR}/summary.json"
  temporary_summary="${summary_path}.tmp"
  {
    printf '{\n'
    printf '  "operation_id": "%s",\n' "$(operation_json_escape "${FLOWFORM_OPERATION_ID}")"
    printf '  "operation": "%s",\n' "$(operation_json_escape "${FLOWFORM_OPERATION_NAME}")"
    printf '  "environment": "%s",\n' "$(operation_json_escape "${FLOWFORM_OPERATION_ENVIRONMENT}")"
    printf '  "source_commit": "%s",\n' "$(operation_json_escape "${FLOWFORM_OPERATION_SOURCE_COMMIT}")"
    printf '  "started_at": "%s",\n' "$(operation_json_escape "${FLOWFORM_OPERATION_STARTED_AT}")"
    printf '  "finished_at": "%s",\n' "$(operation_json_escape "${finished_at}")"
    printf '  "duration_seconds": %d,\n' "${duration_seconds}"
    printf '  "exit_code": %d,\n' "${exit_code}"
    printf '  "outcome": "%s",\n' "${outcome}"
    printf '  "artifact_directory": "%s"' \
      "$(operation_json_escape "${FLOWFORM_OPERATION_ARTIFACT_DIR}")"
    if (( ${#FLOWFORM_OPERATION_SUMMARY_METADATA[@]} > 0 )); then
      mapfile -t metadata_keys < <(
        printf '%s\n' "${!FLOWFORM_OPERATION_SUMMARY_METADATA[@]}" | LC_ALL=C sort
      )
    fi
    for key in "${metadata_keys[@]}"; do
      value="${FLOWFORM_OPERATION_SUMMARY_METADATA[${key}]}"
      printf ',\n  "%s": "%s"' \
        "${key}" \
        "$(operation_json_escape "${value}")"
    done
    printf '\n}\n'
  } > "${temporary_summary}"
  chmod 600 "${temporary_summary}"
  mv -- "${temporary_summary}" "${summary_path}"
  FLOWFORM_OPERATION_FINISHED=1
  FLOWFORM_OPERATION_FINISHING=0

  if (( exit_code == 0 )); then
    operation_log "success" \
      "completed in ${duration_seconds}s; summary=${summary_path}"
  else
    operation_log "error" \
      "failed with exit_code=${exit_code} after ${duration_seconds}s; summary=${summary_path}"
  fi

  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
      printf 'flowform_operation_id=%s\n' "${FLOWFORM_OPERATION_ID}"
      printf 'flowform_operation_artifact_dir=%s\n' "${FLOWFORM_OPERATION_ARTIFACT_DIR}"
      printf 'flowform_operation_summary=%s\n' "${summary_path}"
    } >> "${GITHUB_OUTPUT}" 2>/dev/null || true
  fi
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      printf '### FlowForm operation: `%s`\n\n' "${FLOWFORM_OPERATION_NAME}"
      printf -- '- Result: **%s** (exit `%s`, %ss)\n' "${outcome}" "${exit_code}" "${duration_seconds}"
      printf -- '- Environment: `%s`\n' "${FLOWFORM_OPERATION_ENVIRONMENT}"
      printf -- '- Operation ID: `%s`\n' "${FLOWFORM_OPERATION_ID}"
      printf -- '- Artifacts: `%s`\n' "${FLOWFORM_OPERATION_ARTIFACT_DIR}"
    } >> "${GITHUB_STEP_SUMMARY}" 2>/dev/null || true
  fi
}

operation_die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 2
}

operation_todo() {
  printf 'TODO: %s\n' "$*" >&2
  exit 3
}

require_executable() {
  [[ -x "$1" ]] || operation_die "required executable is unavailable: $1"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 \
    || operation_die "required command is unavailable: $1"
}

validate_environment() {
  case "$1" in
    dev|staging|prod) ;;
    *) operation_die "environment must be dev, staging, or prod" ;;
  esac
}

validate_host_role() {
  case "$1" in
    app|proxy) ;;
    *) operation_die "role must be app or proxy" ;;
  esac
}
