#!/usr/bin/env bash

# shellcheck source=cmd_verify.sh
source "${IMAGE_SCRIPT_DIR}/lib/cmd_verify.sh"

cmd_publish_main() {
  local platform="${1:-}" environment="" role="" dry_run=0
  local parameter ami_id region cdk_account caller_account vars_file
  if [[ "${platform}" == -h || "${platform}" == --help ]]; then
    printf '%s\n' \
      'Usage: image publish aws --environment <dev|staging|prod> --role <app|proxy> [--dry-run]'
    return
  fi
  [[ $# -gt 0 ]] && shift || true
  [[ "${platform}" == aws ]] \
    || die "usage: image publish aws --environment <dev|staging|prod> --role <app|proxy> [--dry-run]"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --environment)
        [[ $# -ge 2 ]] || die "--environment requires a value"
        environment="$2"
        shift 2
        ;;
      --role)
        [[ $# -ge 2 ]] || die "--role requires a value"
        role="$2"
        shift 2
        ;;
      --dry-run)
        dry_run=1
        shift
        ;;
      -h|--help)
        printf '%s\n' \
          'Usage: image publish aws --environment <dev|staging|prod> --role <app|proxy> [--dry-run]'
        return
        ;;
      *) die "unknown publish argument: $1" ;;
    esac
  done

  [[ -n "${environment}" ]] \
    || die "--environment is required; CDK owns distinct AMI parameters per environment"
  [[ "${role}" =~ ^(app|proxy)$ ]] \
    || die "--role must be app or proxy; the base AMI is lineage, not a deployable CDK image"

  phase "preflight AWS ${role} AMI publication"
  image_aws_session_preflight
  parameter="$(image_cdk_ami_parameter "${environment}" "${role}")"
  ami_id="$(image_aws_artifact_id "${role}")"
  region="$(image_cdk_region)"
  cdk_account="$(image_cdk_account)"
  caller_account="$(
    aws sts get-caller-identity \
      --profile "${AWS_PROFILE}" \
      --query Account \
      --output text \
      --no-cli-pager
  )"
  [[ "${caller_account}" == "${cdk_account}" ]] \
    || die "AWS profile ${AWS_PROFILE} targets account ${caller_account}, but CDK owns account ${cdk_account}; refusing to publish"

  vars_file="${PACKER_DIR}/variables/aws.auto.pkrvars.hcl"
  _image_verify_aws "${role}" --vars-file "${vars_file}"
  log "CDK environment=${environment} role=${role} account=${cdk_account} parameter=${parameter} region=${region} AMI=${ami_id}"
  if (( dry_run == 1 )); then
    success "dry run complete; no SSM parameter was changed"
    return
  fi

  phase "publish verified ${role} AMI for CDK consumption"
  aws ssm put-parameter \
    --profile "${AWS_PROFILE}" \
    --region "${region}" \
    --name "${parameter}" \
    --type String \
    --value "${ami_id}" \
    --overwrite \
    --no-cli-pager >/dev/null
  success "published ${ami_id} to ${parameter}; ${environment} CDK will resolve it at deployment"
}
