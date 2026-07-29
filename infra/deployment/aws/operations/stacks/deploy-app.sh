#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_lib/common.sh
source "${SCRIPT_DIR}/../_lib/common.sh"

usage() {
  printf 'Usage: %s --environment <staging|prod> [--diff-only|--skip-diff] [-- CDK_DEPLOY_ARGS]\n' "${0##*/}"
}

environment=""
declare -a mode_args=()
declare -a deploy_args=(--force)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment)
      [[ $# -ge 2 ]] || operation_die "--environment requires a value"
      environment="$2"
      shift 2
      ;;
    --diff-only|--skip-diff)
      mode_args+=("$1")
      shift
      ;;
    --)
      shift
      deploy_args+=("$@")
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) operation_die "unknown argument: $1" ;;
  esac
done

case "${environment}" in
  staging|prod) ;;
  "") usage >&2; exit 2 ;;
  *) operation_die "App stack exists only for staging or prod" ;;
esac

exec "${SCRIPT_DIR}/deploy.sh" \
  --environment "${environment}" \
  --stack "FlowForm-${environment^}-App" \
  --exclusively \
  "${mode_args[@]}" \
  -- \
  "${deploy_args[@]}"
