#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_lib/common.sh
source "${SCRIPT_DIR}/../_lib/common.sh"

usage() {
  printf 'Usage: %s <base|app|proxy|all> [--allow-dirty] [image build options]\n' "${0##*/}"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

target="${1:-}"
case "${target}" in
  base|app|proxy|all) shift ;;
  "") usage >&2; exit 2 ;;
  *) operation_die "machine-image target must be base, app, proxy, or all" ;;
esac

allow_dirty=0
validation_only=0
declare -a build_args=()
for argument in "$@"; do
  case "${argument}" in
    --allow-dirty) allow_dirty=1 ;;
    --validate-only|--syntax-only)
      validation_only=1
      build_args+=("${argument}")
      ;;
    *) build_args+=("${argument}") ;;
  esac
done

if (( validation_only == 0 && allow_dirty == 0 )); then
  [[ -z "$(git -C "${REPO_ROOT}" status --porcelain --untracked-files=normal)" ]] \
    || operation_die "a live AMI build requires a clean worktree; commit the exact source or pass --allow-dirty deliberately"
fi

require_executable "${FLOWFORM_IMAGE_TOOL}"
exec "${FLOWFORM_IMAGE_TOOL}" build aws "${target}" "${build_args[@]}"
