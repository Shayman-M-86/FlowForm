#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_lib/common.sh
source "${SCRIPT_DIR}/../_lib/common.sh"

usage() {
  printf 'Usage: %s <base|app|proxy> [AMI verification options]\n' "${0##*/}"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

role="${1:-}"
case "${role}" in
  base|app|proxy) shift ;;
  "") usage >&2; exit 2 ;;
  *) operation_die "machine-image role must be base, app, or proxy" ;;
esac

require_executable "${FLOWFORM_IMAGE_TOOL}"
exec "${FLOWFORM_IMAGE_TOOL}" verify aws "${role}" "$@"

