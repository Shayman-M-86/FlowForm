#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_lib/common.sh
source "${SCRIPT_DIR}/../_lib/common.sh"

usage() {
  cat <<USAGE
Usage: ${0##*/} --environment <dev|staging|prod> [options]

Options:
  --release-manifest PATH  Previously published digest manifest.
  --dry-run                Show both role-manifest updates without writing SSM.
USAGE
}

environment=""
dry_run=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment)
      [[ $# -ge 2 ]] || operation_die "--environment requires a value"
      environment="$2"
      shift 2
      ;;
    --release-manifest)
      [[ $# -ge 2 ]] || operation_die "--release-manifest requires a path"
      RELEASE_MANIFEST_PATH="$2"
      export RELEASE_MANIFEST_PATH
      shift 2
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) operation_die "unknown argument: $1" ;;
  esac
done

[[ -n "${environment}" ]] || { usage >&2; exit 2; }
validate_environment "${environment}"
export FLOWFORM_ENVIRONMENT="${environment}"
if (( dry_run == 1 )); then
  export DRY_RUN=1
fi

require_executable "${FLOWFORM_CONTAINER_PUBLISHER}"
exec "${FLOWFORM_CONTAINER_PUBLISHER}" promote

