#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_lib/common.sh
source "${SCRIPT_DIR}/../_lib/common.sh"

usage() {
  cat <<USAGE
Usage: ${0##*/} --environment <staging|prod> --role <app|proxy> [options] [-- CDK_DEPLOY_ARGS]

Options:
  --diff-only, --dry-run  Preview the selected role stack without replacing it.
  --skip-diff             Replace the role without first running CDK diff.

The selected role stack is always deployed exclusively and with --force so
CloudFormation re-resolves its published AMI parameter.
USAGE
}

environment=""
role=""
declare -a mode_args=()
declare -a deploy_args=(--force)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment)
      [[ $# -ge 2 ]] || operation_die "--environment requires a value"
      environment="$2"
      shift 2
      ;;
    --role)
      [[ $# -ge 2 ]] || operation_die "--role requires a value"
      role="$2"
      shift 2
      ;;
    --diff-only|--dry-run)
      mode_args=(--diff-only)
      shift
      ;;
    --skip-diff)
      mode_args=(--skip-diff)
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
  *) operation_die "host replacement is available only for staging or prod" ;;
esac
validate_host_role "${role}"

exec "${SCRIPT_DIR}/../stacks/deploy.sh" \
  --environment "${environment}" \
  --stack "FlowForm-${environment^}-${role^}" \
  --exclusively \
  "${mode_args[@]}" \
  -- \
  "${deploy_args[@]}"
