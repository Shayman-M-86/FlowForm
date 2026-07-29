#!/usr/bin/env bash

_image_verify_aws() {
  local role="${1:-}"
  [[ "${role}" =~ ^(base|app|proxy)$ ]] || die "AWS verify role must be base, app, or proxy"
  shift
  image_aws_session_preflight
  PACKER_DIR="${PACKER_DIR}" bash "${IMAGE_SCRIPT_DIR}/lib/actions/aws-ami-verify.sh" \
    --role "${role}" --manifest "$(image_aws_manifest "${role}")" "$@"
}

_image_verify_proxmox() {
  local config="" index
  for ((index = 1; index <= $#; index++)); do
    if [[ "${!index}" == --env-file ]]; then
      index=$((index + 1))
      [[ index -le $# ]] || die "--env-file requires a path"
      config="${!index}"
      break
    fi
  done
  config="${config:-$(image_proxmox_config_file)}"
  IMAGE_CONFIG_FILE="${config}" bash "${IMAGE_SCRIPT_DIR}/lib/actions/proxmox-disk-verify.sh" \
    --env-file "${config}" "$@"
}

cmd_verify_main() {
  local platform="${1:-}"
  [[ $# -gt 0 ]] && shift || true
  case "${platform}" in
    aws)
      local role="${1:-}"
      [[ $# -gt 0 ]] && shift || true
      phase "verify AWS ${role} AMI and snapshot contract"
      _image_verify_aws "${role}" "$@"
      ;;
    proxmox) phase "verify Proxmox source and template disk policy"; _image_verify_proxmox "$@" ;;
    all)
      [[ $# -eq 0 ]] || die "image verify all accepts no extra arguments"
      phase "verify AWS base AMI and snapshot contract"; _image_verify_aws base
      phase "verify Proxmox source and template disk policy"; _image_verify_proxmox
      ;;
    -h|--help) printf '%s\n' 'Usage: image verify aws <base|app|proxy> [options]' '       image verify proxmox [options]' ;;
    *) die "usage: image verify aws <base|app|proxy> [options] | image verify proxmox [options]" ;;
  esac
}
