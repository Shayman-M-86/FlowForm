#!/usr/bin/env bash

cmd_prepare_main() {
  local platform="${1:-}" config="" index
  if [[ "${platform}" == -h || "${platform}" == --help ]]; then
    printf '%s\n' 'Usage: image prepare proxmox [--apply] [--replace] [--env-file PATH]'
    return
  fi
  [[ $# -gt 0 ]] && shift || true
  [[ "${platform}" == proxmox ]] || die "usage: image prepare proxmox [--apply] [--replace] [--env-file PATH]"
  case " ${*} " in *' --help '*|*' -h '*)
    bash "${IMAGE_SCRIPT_DIR}/lib/actions/proxmox-source.sh" --help
    return
  esac
  for ((index = 1; index <= $#; index++)); do
    if [[ "${!index}" == --env-file ]]; then
      index=$((index + 1))
      [[ index -le $# ]] || die "--env-file requires a path"
      config="${!index}"
      break
    fi
  done
  config="${config:-$(image_proxmox_config_file)}"
  phase "prepare Proxmox source template"
  IMAGE_CONFIG_FILE="${config}" bash "${IMAGE_SCRIPT_DIR}/lib/actions/proxmox-source.sh" \
    --env-file "${config}" "$@"
}
