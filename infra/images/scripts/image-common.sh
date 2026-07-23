#!/usr/bin/env bash
# Shared workstation-side support for the `image` dispatcher.

if [[ -n "${_FLOWFORM_IMAGE_COMMON_SOURCED:-}" ]]; then return; fi
_FLOWFORM_IMAGE_COMMON_SOURCED=1

IMAGE_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_ROOT="$(cd -- "${IMAGE_SCRIPT_DIR}/.." && pwd)"
PACKER_DIR="${IMAGE_ROOT}/packer"
IMAGE_CONFIG_DIR="${IMAGE_ROOT}/config"
IMAGE_CONFIG_FILE="${IMAGE_CONFIG_FILE:-${IMAGE_CONFIG_DIR}/proxmox-source.env}"
IMAGE_CDK_ROOT="$(cd -- "${IMAGE_ROOT}/../deployment/aws/cdk" && pwd)"
IMAGE_SUBCOMMAND="${IMAGE_SUBCOMMAND:-image}"
IMAGE_COLOR="${IMAGE_COLOR:-auto}"

_image_colour_enabled() {
  local fd="$1"
  [[ -z "${NO_COLOR:-}" ]] || return 1
  case "${IMAGE_COLOR}" in
    always) return 0 ;;
    never) return 1 ;;
    auto) [[ -t "${fd}" ]] ;;
    *) return 1 ;;
  esac
}

_image_emit() { # fd LEVEL message...
  local fd="$1" level="$2" colour="" reset=""; shift 2
  if _image_colour_enabled "${fd}"; then
    reset=$'\033[0m'
    case "${level}" in
      PHASE) colour=$'\033[1;35m' ;;
      INFO) colour=$'\033[0;36m' ;;
      SUCCESS) colour=$'\033[1;32m' ;;
      WARN) colour=$'\033[1;33m' ;;
      ERROR) colour=$'\033[1;31m' ;;
    esac
  fi
  printf '%s | %b%-7s%b | %-22s | %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    "${colour}" "${level}" "${reset}" "${IMAGE_SUBCOMMAND}" "$*" >&"${fd}"
}

log() { _image_emit 2 INFO "$*"; }
phase() { IMAGE_CURRENT_PHASE="$*"; _image_emit 2 PHASE "$*"; }
success() { _image_emit 2 SUCCESS "$*"; }
warn() { _image_emit 2 WARN "$*"; }
error() { _image_emit 2 ERROR "$*"; }
die() { error "$*"; exit 1; }

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

require_file() {
  local path="$1" recovery="$2"
  [[ -f "${path}" ]] || die "required file missing: ${path}. ${recovery}"
}

image_proxmox_config_file() {
  if [[ -f "${IMAGE_CONFIG_FILE}" ]]; then
    printf '%s' "${IMAGE_CONFIG_FILE}"
    return
  fi
  local legacy="${IMAGE_SCRIPT_DIR}/.env"
  if [[ -f "${legacy}" ]]; then
    warn "using legacy ${legacy}; move it to ${IMAGE_CONFIG_FILE}"
    printf '%s' "${legacy}"
    return
  fi
  die "Proxmox source config missing. Copy ${IMAGE_CONFIG_DIR}/proxmox-source.env.example to ${IMAGE_CONFIG_FILE} and fill it in"
}

image_aws_session_preflight() {
  require_command aws
  export AWS_PROFILE="${AWS_PROFILE:-flowform-dev}"
  local output login_profile source_profile depth=0
  if output="$(aws sts get-caller-identity --profile "${AWS_PROFILE}" --output json --no-cli-pager 2>&1)"; then
    log "AWS session valid for profile ${AWS_PROFILE}"
    return 0
  fi
  case "${output}" in
    *ExpiredToken*|*expired*|*SSO*login*|*not*logged*in*|*credential*process*)
      login_profile="${AWS_PROFILE}"
      while (( depth < 10 )); do
        source_profile="$(aws configure get source_profile --profile "${login_profile}" 2>/dev/null || true)"
        [[ -n "${source_profile}" ]] || break
        login_profile="${source_profile}"
        depth=$((depth + 1))
      done
      [[ "${login_profile}" == "${AWS_PROFILE}" ]] \
        || log "AWS profile ${AWS_PROFILE} assumes a role through source profile ${login_profile}"
      die "AWS profile ${AWS_PROFILE} is logged out or expired. Run 'aws login --profile ${login_profile}', then rerun the image command"
      ;;
    *) die "AWS identity check failed for profile ${AWS_PROFILE}; refusing to treat it as a login expiry. AWS CLI said: ${output}" ;;
  esac
}

image_aws_artifact_id() { # [manifest]
  local manifest="${1:-${PACKER_DIR}/manifests/packer-manifest.json}" ami_id
  require_command jq
  require_file "${manifest}" "Run 'infra/images/scripts/image build aws' first"
  ami_id="$(jq -er '
    .builds | map(select(.builder_type == "amazon-ebs")) | last | .artifact_id // empty
    | select(type == "string") | split(":") | .[1] // empty
  ' "${manifest}")" || die "no amazon-ebs artifact found in ${manifest}; run 'infra/images/scripts/image build aws' first"
  [[ "${ami_id}" =~ ^ami-[0-9a-f]+$ ]] || die "invalid AWS AMI ID in ${manifest}: ${ami_id}"
  printf '%s' "${ami_id}"
}

image_cdk_ami_parameter() { # dev|staging|prod
  local environment="$1" config="${IMAGE_CDK_ROOT}/flowform_infra/config/environments.py" parameter
  [[ "${environment}" =~ ^(dev|staging|prod)$ ]] || die "AWS environment must be dev, staging, or prod"
  require_file "${config}" "The CDK environment configuration owns the AMI parameter contract"
  parameter="$(awk -v start="\"${environment}\": EnvConfig(" '
    index($0, start) { inside=1 }
    inside && /ec2_base_ami_ssm_parameter=/ {
      line=$0; sub(/^[^"]*"/, "", line); sub(/".*/, "", line); print line; exit
    }
    inside && /^    \),/ { exit }
  ' "${config}")"
  [[ "${parameter}" == /flowform/*/ec2/baseAmiId ]] \
    || die "CDK environment ${environment} has no usable ec2_base_ami_ssm_parameter"
  printf '%s' "${parameter}"
}

image_cdk_region() {
  local config="${IMAGE_CDK_ROOT}/flowform_infra/config/environments.py" region
  region="$(awk -F '"' '/^_DEFAULT_REGION = / { print $2; exit }' "${config}")"
  [[ "${region}" =~ ^[a-z]{2}-[a-z]+-[0-9]+$ ]] || die "could not resolve the CDK default AWS region"
  printf '%s' "${region}"
}

image_cdk_account() {
  local config="${IMAGE_CDK_ROOT}/flowform_infra/config/environments.py" account
  account="$(awk -F '"' '/^_ACCOUNT = / { print $2; exit }' "${config}")"
  [[ "${account}" =~ ^[0-9]{12}$ ]] || die "could not resolve the CDK AWS account"
  printf '%s' "${account}"
}
