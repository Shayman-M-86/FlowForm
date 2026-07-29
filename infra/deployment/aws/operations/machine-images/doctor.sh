#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_lib/common.sh
source "${SCRIPT_DIR}/../_lib/common.sh"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  printf 'Usage: %s\n' "${0##*/}"
  exit 0
fi
[[ $# -eq 0 ]] || operation_die "usage: ${0##*/}"

require_executable "${FLOWFORM_IMAGE_TOOL}"
exec "${FLOWFORM_IMAGE_TOOL}" doctor aws

