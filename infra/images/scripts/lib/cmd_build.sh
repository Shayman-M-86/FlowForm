#!/usr/bin/env bash

# shellcheck source=packer-project.sh
source "${IMAGE_SCRIPT_DIR}/lib/packer-project.sh"
# shellcheck source=cmd_verify.sh
source "${IMAGE_SCRIPT_DIR}/lib/cmd_verify.sh"

_image_validate_aws_vars() {
  local vars_file="$1" source_name owner architecture size
  source_name="$(awk -F '"' '$1 ~ /^[[:space:]]*aws_source_ami_name[[:space:]]*=/ { print $2; exit }' "${vars_file}")"
  owner="$(awk -F '"' '$1 ~ /^[[:space:]]*aws_source_ami_owner[[:space:]]*=/ { print $2; exit }' "${vars_file}")"
  architecture="$(awk -F '"' '$1 ~ /^[[:space:]]*aws_architecture[[:space:]]*=/ { print $2; exit }' "${vars_file}")"
  size="$(awk -F '=' '$1 ~ /^[[:space:]]*aws_root_volume_size[[:space:]]*$/ { gsub(/[[:space:]]/, "", $2); print $2; exit }' "${vars_file}")"
  [[ "${owner}" == amazon ]] || die "aws_source_ami_owner must be the verified Amazon owner alias"
  [[ "${source_name}" == al2023-ami-minimal-2023.*-kernel-6.1-x86_64 ]] \
    || die "aws_source_ami_name must select the x86_64 AL2023 minimal kernel-6.1 AMI"
  [[ "${architecture}" == x86_64 ]] || die "aws_architecture must be x86_64"
  [[ "${size}" =~ ^[0-9]+$ ]] || die "aws_root_volume_size must be an integer GiB value"
  (( size >= 8 && size <= 12 )) || die "aws_root_volume_size must be between 8 and 12 GiB"
}

_image_build_proxmox_target() { # target verify-after
  local target="$1" verify_after="$2" vars_file build_file only_target vmids
  vars_file="${PACKER_DIR}/variables/proxmox.auto.pkrvars.hcl"
  require_vars_file "${vars_file}" "proxmox.auto.pkrvars.hcl.example"
  assert_proxmox_build_ip_available "${vars_file}"
  case "${target}" in
    golden)
      build_file="${PACKER_DIR}/builds/golden.pkr.hcl"
      only_target="flowform-golden.proxmox-clone.amazon_linux_2023"
      vmids="8999 9000"
      ;;
    localstack)
      build_file="${PACKER_DIR}/builds/localstack-fixture.pkr.hcl"
      only_target="flowform-localstack-fixture.proxmox-clone.localstack_fixture"
      vmids="8999 9000 9001"
      ;;
    db)
      build_file="${PACKER_DIR}/builds/db-fixture.pkr.hcl"
      only_target="flowform-db-fixture.proxmox-clone.db_fixture"
      vmids="8999 9000 9001 9002"
      ;;
    *) die "unknown Proxmox build target: ${target}" ;;
  esac
  phase "build Proxmox ${target} image"
  run_packer_build "${build_file}" "${only_target}" "${vars_file}"
  if [[ "${PACKER_VALIDATE_ONLY:-0}" != 1 && "${verify_after}" == 1 ]]; then
    phase "verify Proxmox disk policy after ${target} build"
    # shellcheck disable=SC2086
    _image_verify_proxmox ${vmids}
  fi
}

cmd_build_main() {
  local platform="${1:-}" target="" validate_only=0 syntax_only=0
  if [[ "${platform}" == -h || "${platform}" == --help ]]; then
    printf '%s\n' 'Usage: image build aws [--validate-only] [--syntax-only]' \
      '       image build proxmox <golden|localstack|db|all> [--validate-only] [--syntax-only]'
    return
  fi
  [[ $# -gt 0 ]] && shift || true
  if [[ "${platform}" == proxmox ]]; then
    target="${1:-}"
    [[ $# -gt 0 ]] && shift || true
  fi
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --validate-only) validate_only=1; shift ;;
      --syntax-only) syntax_only=1; validate_only=1; shift ;;
      -h|--help)
        printf '%s\n' 'Usage: image build aws [--validate-only] [--syntax-only]' \
          '       image build proxmox <golden|localstack|db|all> [--validate-only] [--syntax-only]'
        return
        ;;
      *) die "unknown build argument: $1" ;;
    esac
  done
  export PACKER_VALIDATE_ONLY="${validate_only}"
  export PACKER_SYNTAX_ONLY="${syntax_only}"
  case "${platform}" in
    aws)
      local vars_file="${PACKER_DIR}/variables/aws.auto.pkrvars.hcl"
      require_vars_file "${vars_file}" "aws.auto.pkrvars.hcl.example"
      _image_validate_aws_vars "${vars_file}"
      (( validate_only == 1 )) || image_aws_session_preflight
      phase "build AWS golden AMI"
      run_packer_build "${PACKER_DIR}/builds/golden.pkr.hcl" \
        "flowform-golden.amazon-ebs.amazon_linux_2023" "${vars_file}"
      if (( validate_only == 0 )); then
        phase "verify AWS AMI for CDK consumption"
        _image_verify_aws --vars-file "${vars_file}"
      fi
      ;;
    proxmox)
      case "${target}" in
        golden|localstack|db) _image_build_proxmox_target "${target}" 1 ;;
        all)
          if (( validate_only == 0 )); then
            local config
            config="$(image_proxmox_config_file)"
            phase "preflight Proxmox source template"
            IMAGE_CONFIG_FILE="${config}" bash "${IMAGE_SCRIPT_DIR}/lib/actions/proxmox-source.sh" \
              --env-file "${config}"
          fi
          _image_build_proxmox_target golden 0
          _image_build_proxmox_target localstack 0
          _image_build_proxmox_target db 0
          if (( validate_only == 0 )); then
            phase "verify complete Proxmox image lineage"
            _image_verify_proxmox 8999 9000 9001 9002
          fi
          ;;
        *) die "usage: image build proxmox <golden|localstack|db|all> [--validate-only] [--syntax-only]" ;;
      esac
      ;;
    *) die "usage: image build <aws|proxmox> ..." ;;
  esac
}
