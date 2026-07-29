#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_ROOT="$(cd -- "${SCRIPT_LIB_DIR}/../.." && pwd)"
# Source of the host convergence assets baked into the golden image.
REPO_ROOT="$(cd -- "${IMAGE_ROOT}/../.." && pwd)"
PACKER_DIR="${IMAGE_ROOT}/packer"

# The dispatcher provides structured versions. Keep small fallbacks so the
# validation suite can source this focused library directly.
declare -F die >/dev/null || die() { printf '[flowform-packer] ERROR: %s\n' "$*" >&2; exit 1; }
declare -F log >/dev/null || log() { printf '[flowform-packer] %s\n' "$*"; }
declare -F success >/dev/null || success() { log "$*"; }
declare -F require_command >/dev/null || require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

require_vars_file() {
  local vars_file="$1"
  local example_name="$2"
  [[ -f "${vars_file}" ]] \
    || die "missing ${vars_file}; copy ${PACKER_DIR}/variables/${example_name} and fill it in"
}

assert_proxmox_build_ip_available() {
  local vars_file="$1"
  local build_ip_cidr build_ip
  build_ip_cidr="$(awk -F'"' \
    '$1 ~ /^[[:space:]]*proxmox_build_ip_cidr[[:space:]]*=[[:space:]]*$/ { print $2; exit }' \
    "${vars_file}")"
  [[ "${build_ip_cidr}" == */* ]] \
    || die "proxmox_build_ip_cidr is missing or invalid in ${vars_file}"
  build_ip="${build_ip_cidr%%/*}"
  if command -v ping >/dev/null 2>&1 && ping -c 1 -W 1 "${build_ip}" >/dev/null 2>&1; then
    die "dedicated Packer address ${build_ip} is already responding"
  fi
}

run_packer_build() (
  local build_file="$1"
  local only_target="$2"
  local vars_file="$3"
  shift 3
  local project_dir original_aws_config original_aws_profile packer_aws_config
  local credential_helper aws_region source_commit diagnostic_report="" diagnostic_role
  local diagnostic_dir="" diagnostics_pid="" packer_log_path=""
  local failure_snapshot_request="" failure_snapshot_complete=""
  local -a validate_args
  local -a extra_args=("$@")

  require_command packer
  require_command git
  if [[ "${only_target}" == *.amazon-ebs.* ]] \
      && [[ "${PACKER_VALIDATE_ONLY:-0}" != "1" ]]; then
    require_command session-manager-plugin
  fi
  [[ -f "${build_file}" ]] || die "Packer build file not found: ${build_file}"
  [[ -f "${vars_file}" ]] || die "Packer variable file not found: ${vars_file}"
  build_file="$(realpath -- "${build_file}")"
  vars_file="$(realpath -- "${vars_file}")"
  source_commit="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
  [[ "${source_commit}" =~ ^[0-9a-f]{40}$ ]] \
    || die "could not resolve a full source commit for the machine image"

  project_dir="$(mktemp -d)"
  cleanup_packer_project() {
    local status=$?
    trap - EXIT
    if [[ -n "${diagnostics_pid}" ]]; then
      kill "${diagnostics_pid}" >/dev/null 2>&1 || true
      wait "${diagnostics_pid}" >/dev/null 2>&1 || true
    fi
    [[ -z "${failure_snapshot_request}" ]] \
      || rm -f "${failure_snapshot_request}" "${failure_snapshot_complete}"
    if [[ -n "${diagnostic_report}" ]]; then
      log "Packer diagnostics directory: ${diagnostic_dir}"
      log "AWS builder diagnostic report: ${diagnostic_report}"
      if (( status == 0 )); then
        rm -f -- "${packer_log_path}"
        log "Packer debug log discarded after successful build; it is retained only for failures"
      else
        log "Packer debug log: ${packer_log_path}"
      fi
    fi
    rm -rf "${project_dir}"
    exit "${status}"
  }
  trap cleanup_packer_project EXIT

  request_failure_snapshot() {
    [[ -n "${diagnostics_pid}" ]] || return 0
    log "Packer failed; requesting a final EC2 status and console-output snapshot"
    : >"${failure_snapshot_request}"
    chmod 0600 "${failure_snapshot_request}"
    local attempt
    for attempt in {1..30}; do
      [[ ! -e "${failure_snapshot_complete}" ]] || return 0
      kill -0 "${diagnostics_pid}" >/dev/null 2>&1 || break
      sleep 0.5
    done
    warn "the final diagnostic snapshot did not acknowledge within 15 seconds; the live report collected all preceding builder state"
  }

  # AWS CLI login sessions are understood by the CLI but not yet by the AWS
  # SDK bundled with Packer's Amazon plugin. Bridge that supported CLI session
  # through the SDK's credential_process provider. The helper emits credentials
  # only to Packer on demand, can refresh them during a longer AMI build, and
  # stores no credential material on disk.
  if [[ "${only_target}" == *.amazon-ebs.* ]] \
      && [[ -n "${AWS_PROFILE:-}" ]] \
      && [[ -n "$(aws configure get login_session --profile "${AWS_PROFILE}" 2>/dev/null || true)" ]]; then
    original_aws_profile="${AWS_PROFILE}"
    original_aws_config="${AWS_CONFIG_FILE:-${HOME}/.aws/config}"
    credential_helper="${project_dir}/aws-credential-process.sh"
    packer_aws_config="${project_dir}/aws-config"
    aws_region="$(aws configure get region --profile "${original_aws_profile}")"

    printf '%s\n' \
      '#!/usr/bin/env bash' \
      'set -Eeuo pipefail' \
      "exec env AWS_CONFIG_FILE=$(printf '%q' "${original_aws_config}") aws configure export-credentials --profile $(printf '%q' "${original_aws_profile}") --format process" \
      >"${credential_helper}"
    chmod 0700 "${credential_helper}"
    printf '[profile flowform-packer]\ncredential_process = %s\nregion = %s\n' \
      "${credential_helper}" "${aws_region}" >"${packer_aws_config}"
    chmod 0600 "${packer_aws_config}"

    export AWS_CONFIG_FILE="${packer_aws_config}"
    export AWS_PROFILE="flowform-packer"
    export AWS_SDK_LOAD_CONFIG=1
    log "configured Packer credential_process bridge for AWS CLI login profile ${original_aws_profile}"
  fi

  ln -s "${PACKER_DIR}/plugins.pkr.hcl" "${project_dir}/plugins.pkr.hcl"
  ln -s "${PACKER_DIR}/locals.pkr.hcl" "${project_dir}/locals.pkr.hcl"
  for config_file in "${PACKER_DIR}"/sources/*.pkr.hcl; do
    ln -s "${config_file}" "${project_dir}/source-$(basename -- "${config_file}")"
  done
  for config_file in "${PACKER_DIR}"/variables/*.pkr.hcl; do
    ln -s "${config_file}" "${project_dir}/variable-$(basename -- "${config_file}")"
  done
  ln -s "${build_file}" "${project_dir}/build-$(basename -- "${build_file}")"

  log "initializing Packer project for $(basename -- "${build_file}")"
  packer init "${project_dir}"
  log "validating Packer target ${only_target}"
  validate_args=(
    -only="${only_target}"
    -var "image_root=${IMAGE_ROOT}"
    -var "repo_root=${REPO_ROOT}"
    -var-file="${vars_file}"
    -var "source_commit=${source_commit}"
    "${extra_args[@]}"
  )
  if [[ "${PACKER_SYNTAX_ONLY:-0}" == "1" ]]; then
    validate_args=(-syntax-only "${validate_args[@]}")
  fi
  packer validate "${validate_args[@]}" "${project_dir}"

  if [[ "${PACKER_VALIDATE_ONLY:-0}" == "1" ]]; then
    success "Packer validation complete for ${only_target}"
    exit 0
  fi

  if [[ "${PACKER_DIAGNOSTICS:-0}" == "1" ]]; then
    require_command aws
    aws_region="$(
      awk -F'"' '$1 ~ /^[[:space:]]*aws_region[[:space:]]*=/ { print $2; exit }' \
        "${vars_file}"
    )"
    [[ -n "${aws_region}" ]] || die "could not resolve aws_region for AWS builder diagnostics"
    case "${only_target}" in
      *amazon_linux_2023_base) diagnostic_role="base" ;;
      *flowform_role)
        local argument
        for argument in "${extra_args[@]}"; do
          case "${argument}" in
            image_role=*) diagnostic_role="${argument#*=}"; break ;;
          esac
        done
        ;;
      *) die "could not resolve image role for AWS builder diagnostics from ${only_target}" ;;
    esac
    [[ "${diagnostic_role}" =~ ^(base|app|proxy)$ ]] \
      || die "invalid image role for AWS builder diagnostics: ${diagnostic_role}"
    local diagnostic_root operation_slug="standalone" diagnostic_stem
    diagnostic_root="${FLOWFORM_OPERATION_ARTIFACT_DIR:-${FLOWFORM_OPERATION_LOG_DIR:-}}"
    if [[ -n "${diagnostic_root}" ]]; then
      [[ "${diagnostic_root}" == /* ]] \
        || die "operation artifact directory must be an absolute path: ${diagnostic_root}"
      diagnostic_dir="${diagnostic_root}/packer"
      [[ ! -L "${diagnostic_dir}" ]] \
        || die "refusing to write Packer diagnostics through a symbolic link: ${diagnostic_dir}"
      mkdir -p "${diagnostic_dir}"
      chmod 0700 "${diagnostic_dir}"
    else
      diagnostic_dir="$(
        umask 077
        mktemp -d "${TMPDIR:-/tmp}/flowform-packer-diagnostics-XXXXXX"
      )"
    fi
    if [[ "${FLOWFORM_OPERATION_ID:-}" =~ ^[[:alnum:]][[:alnum:]._-]{0,127}$ ]]; then
      operation_slug="${FLOWFORM_OPERATION_ID}"
    fi
    diagnostic_stem="${diagnostic_dir}/packer-${diagnostic_role}-${source_commit:0:12}-${operation_slug}-$(date -u '+%Y%m%dT%H%M%SZ')-${BASHPID}"
    diagnostic_report="${diagnostic_stem}.diagnostics.log"
    packer_log_path="${diagnostic_stem}.debug.log"
    failure_snapshot_request="${diagnostic_stem}.failure-request"
    failure_snapshot_complete="${diagnostic_stem}.failure-complete"
    umask 077
    : >"${diagnostic_report}"
    : >"${packer_log_path}"
    chmod 0600 "${diagnostic_report}" "${packer_log_path}"
    export PACKER_LOG=1
    export PACKER_LOG_PATH="${packer_log_path}"
    log "AWS builder diagnostics enabled; pre-cleanup state streams to ${diagnostic_report}"
    log "Packer debug log will be retained locally and is not shipped: ${packer_log_path}"
    bash "${IMAGE_SCRIPT_DIR}/lib/actions/aws-packer-diagnostics.sh" \
      "${aws_region}" "${source_commit}" "${diagnostic_role}" \
      "${diagnostic_report}" "${failure_snapshot_request}" \
      "${failure_snapshot_complete}" &
    diagnostics_pid=$!
  fi

  log "building Packer target ${only_target}"
  local packer_status
  if packer build \
      -timestamp-ui \
      -on-error="${PACKER_ON_ERROR:-cleanup}" \
      -only="${only_target}" \
      -var "image_root=${IMAGE_ROOT}" \
      -var "repo_root=${REPO_ROOT}" \
      -var-file="${vars_file}" \
      -var "source_commit=${source_commit}" \
      "${extra_args[@]}" \
      "${project_dir}"; then
    packer_status=0
  else
    packer_status=$?
  fi
  if (( packer_status != 0 )); then
    request_failure_snapshot
    error "Packer build failed; diagnostics were preserved before this command returned"
    return "${packer_status}"
  fi
)
