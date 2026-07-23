#!/usr/bin/env bash

cmd_artifact_main() {
  local platform="${1:-}" manifest=""
  if [[ "${platform}" == -h || "${platform}" == --help ]]; then
    printf '%s\n' 'Usage: image artifact aws [--manifest PATH]'
    return
  fi
  [[ $# -gt 0 ]] && shift || true
  [[ "${platform}" == aws ]] || die "usage: image artifact aws [--manifest PATH]"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --manifest) [[ $# -ge 2 ]] || die "--manifest requires a path"; manifest="$2"; shift 2 ;;
      -h|--help) printf '%s\n' 'Usage: image artifact aws [--manifest PATH]'; return ;;
      *) die "unknown artifact argument: $1" ;;
    esac
  done
  phase "read latest AWS image artifact"
  image_aws_artifact_id "${manifest:-${PACKER_DIR}/manifests/packer-manifest.json}"
  printf '\n'
}
