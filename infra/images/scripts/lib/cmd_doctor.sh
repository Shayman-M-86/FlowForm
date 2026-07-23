#!/usr/bin/env bash

# Reuse the build-policy validators without exposing a second implementation.
# shellcheck source=cmd_build.sh
source "${IMAGE_SCRIPT_DIR}/lib/cmd_build.sh"

_image_doctor_aws() {
  phase "check AWS image-build prerequisites"
  for tool in packer aws jq; do require_command "${tool}"; done
  require_vars_file "${PACKER_DIR}/variables/aws.auto.pkrvars.hcl" "aws.auto.pkrvars.hcl.example"
  _image_validate_aws_vars "${PACKER_DIR}/variables/aws.auto.pkrvars.hcl"
  image_aws_session_preflight
  for environment in dev staging prod; do
    log "CDK ${environment} AMI parameter: $(image_cdk_ami_parameter "${environment}")"
  done
}

_image_doctor_proxmox() {
  local config
  phase "check Proxmox image-build prerequisites"
  for tool in packer ssh jq; do require_command "${tool}"; done
  require_vars_file "${PACKER_DIR}/variables/proxmox.auto.pkrvars.hcl" "proxmox.auto.pkrvars.hcl.example"
  assert_proxmox_build_ip_available "${PACKER_DIR}/variables/proxmox.auto.pkrvars.hcl"
  config="$(image_proxmox_config_file)"
  IMAGE_CONFIG_FILE="${config}" bash "${IMAGE_SCRIPT_DIR}/lib/actions/proxmox-source.sh" \
    --env-file "${config}"
}

cmd_doctor_main() {
  local platform="${1:-}"
  [[ $# -le 1 ]] || die "usage: image doctor <aws|proxmox|all>"
  case "${platform}" in
    aws) _image_doctor_aws ;;
    proxmox) _image_doctor_proxmox ;;
    all) _image_doctor_aws; _image_doctor_proxmox ;;
    -h|--help) printf '%s\n' 'Usage: image doctor <aws|proxmox|all>' ;;
    *) die "usage: image doctor <aws|proxmox|all>" ;;
  esac
}
