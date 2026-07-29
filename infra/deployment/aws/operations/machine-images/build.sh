#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_lib/common.sh
source "${SCRIPT_DIR}/../_lib/common.sh"

usage() {
  printf '%s\n' \
    "Usage: ${0##*/} <base|app|proxy|all> [--allow-dirty] [image build options]" \
    '' \
    'Live AWS builds stream Packer output and collect builder diagnostics by default.' \
    'Pass --no-diagnostics to opt out.'
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

operation_init "build-machine-image-${target}" shared
operation_transcript="${FLOWFORM_OPERATION_ARTIFACT_DIR}/packer-output.log"
operation_set_summary_metadata \
  target "${target}" \
  transcript "${operation_transcript}"
operation_install_exit_trap

if (( validation_only == 0 && allow_dirty == 0 )); then
  [[ -z "$(git -C "${REPO_ROOT}" status --porcelain --untracked-files=normal)" ]] \
    || operation_die "a live AMI build requires a clean worktree; commit the exact source or pass --allow-dirty deliberately"
fi

require_executable "${FLOWFORM_IMAGE_TOOL}"
operation_status=0
operation_run_logged "${operation_transcript}" \
  "${FLOWFORM_IMAGE_TOOL}" build aws "${target}" "${build_args[@]}" \
  || operation_status=$?
exit "${operation_status}"
