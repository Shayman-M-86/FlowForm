#!/usr/bin/env bash

cmd_publish_main() {
  local platform="${1:-}" environment="" dry_run=0 parameter ami_id region cdk_account caller_account
  if [[ "${platform}" == -h || "${platform}" == --help ]]; then
    printf '%s\n' 'Usage: image publish aws --environment <dev|staging|prod> [--dry-run]'
    return
  fi
  [[ $# -gt 0 ]] && shift || true
  [[ "${platform}" == aws ]] || die "usage: image publish aws --environment <dev|staging|prod> [--dry-run]"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --environment) [[ $# -ge 2 ]] || die "--environment requires a value"; environment="$2"; shift 2 ;;
      --dry-run) dry_run=1; shift ;;
      -h|--help) printf '%s\n' 'Usage: image publish aws --environment <dev|staging|prod> [--dry-run]'; return ;;
      *) die "unknown publish argument: $1" ;;
    esac
  done
  [[ -n "${environment}" ]] || die "--environment is required; CDK owns a distinct AMI parameter for dev, staging, and prod"
  phase "preflight AWS AMI publication"
  image_aws_session_preflight
  parameter="$(image_cdk_ami_parameter "${environment}")"
  ami_id="$(image_aws_artifact_id)"
  region="$(image_cdk_region)"
  cdk_account="$(image_cdk_account)"
  caller_account="$(aws sts get-caller-identity --profile "${AWS_PROFILE}" --query Account --output text --no-cli-pager)"
  [[ "${caller_account}" == "${cdk_account}" ]] \
    || die "AWS profile ${AWS_PROFILE} targets account ${caller_account}, but CDK owns account ${cdk_account}; refusing to publish"
  PACKER_DIR="${PACKER_DIR}" bash "${IMAGE_SCRIPT_DIR}/lib/actions/aws-ami-verify.sh"
  log "CDK environment=${environment} account=${cdk_account} parameter=${parameter} region=${region} AMI=${ami_id}"
  if (( dry_run == 1 )); then
    success "dry run complete; no SSM parameter was changed"
    return
  fi
  phase "publish verified AMI for CDK consumption"
  aws ssm put-parameter --profile "${AWS_PROFILE}" --region "${region}" \
    --name "${parameter}" --type String --value "${ami_id}" --overwrite --no-cli-pager >/dev/null
  success "published ${ami_id} to ${parameter}; the ${environment} CDK stack will resolve it at deployment"
}
