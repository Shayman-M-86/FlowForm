#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_lib/common.sh
source "${SCRIPT_DIR}/../_lib/common.sh"

usage() {
  cat <<USAGE
Usage: ${0##*/} <validate|publish> [options]

Options:
  --commit SHA             Exact 40-character source commit for publication.
  --release-manifest PATH  Publication output path.
  --source-manifest PATH   Immutable container-source contract.
  --allow-dirty            Deliberately publish from a dirty checkout.
USAGE
}

action="${1:-}"
case "${action}" in
  validate|publish) shift ;;
  -h|--help|"") usage; [[ -n "${action}" ]] && exit 0 || exit 2 ;;
  *) operation_die "action must be validate or publish" ;;
esac

allow_dirty=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --commit)
      [[ $# -ge 2 ]] || operation_die "--commit requires a value"
      RELEASE_COMMIT_SHA="$2"
      export RELEASE_COMMIT_SHA
      shift 2
      ;;
    --release-manifest)
      [[ $# -ge 2 ]] || operation_die "--release-manifest requires a path"
      RELEASE_MANIFEST_PATH="$2"
      export RELEASE_MANIFEST_PATH
      shift 2
      ;;
    --source-manifest)
      [[ $# -ge 2 ]] || operation_die "--source-manifest requires a path"
      SOURCE_MANIFEST="$2"
      export SOURCE_MANIFEST
      shift 2
      ;;
    --allow-dirty)
      allow_dirty=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) operation_die "unknown argument: $1" ;;
  esac
done

if [[ "${action}" == "publish" ]]; then
  release_commit="${RELEASE_COMMIT_SHA:-${GITHUB_SHA:-}}"
  [[ "${release_commit}" =~ ^[0-9a-f]{40}$ ]] \
    || operation_die "publication requires --commit, RELEASE_COMMIT_SHA, or GITHUB_SHA with an exact lowercase commit SHA"
  [[ "$(git -C "${REPO_ROOT}" rev-parse HEAD)" == "${release_commit}" ]] \
    || operation_die "publication commit does not match the checked-out HEAD"
  if (( allow_dirty == 0 )); then
    [[ -z "$(git -C "${REPO_ROOT}" status --porcelain --untracked-files=normal)" ]] \
      || operation_die "container publication requires a clean worktree; commit the exact source or pass --allow-dirty deliberately"
  fi
fi

require_executable "${FLOWFORM_CONTAINER_PUBLISHER}"
exec "${FLOWFORM_CONTAINER_PUBLISHER}" "${action}"
