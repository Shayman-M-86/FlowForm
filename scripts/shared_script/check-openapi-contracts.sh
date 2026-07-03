#!/bin/sh
# CI/CD and pre-commit friendly OpenAPI/generated-contract check.
#
# Run from anywhere:
#   bash scripts/shared_script/check-openapi-contracts.sh

set -eu

export LANG="C.UTF-8"
export LC_ALL="C.UTF-8"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

CHECK_LOG="$(mktemp "${TMPDIR:-/tmp}/flowform-openapi-contracts.XXXXXX.log")"

if bash "${REPO_ROOT}/scripts/shared_script/sync-openapi.sh" --check >"${CHECK_LOG}" 2>&1; then
  rm -f "${CHECK_LOG}"
  exit 0
fi

if grep -q "openapi.yaml is out of date" "${CHECK_LOG}"; then
  cat <<EOF
OpenAPI contract check failed: generated OpenAPI files are out of date.

Run:
  bash scripts/shared_script/sync-openapi.sh

Then stage the generated files and try again:
  git add backend/openapi.yaml \\
    frontend/apps/studio-app/src/api/generated/schema.ts \\
    frontend/apps/studio-app/src/api/generated/rbac.gen.ts \\
    frontend/packages/schema/src/generated

Full check log:
  ${CHECK_LOG}
EOF
  exit 1
fi

if grep -q "diff --git" "${CHECK_LOG}"; then
  cat <<EOF
OpenAPI contract check failed: generated frontend contract files changed.

Run:
  bash scripts/shared_script/sync-openapi.sh

Then stage the generated files and try again.

Full check log:
  ${CHECK_LOG}
EOF
  exit 1
fi

cat <<EOF
OpenAPI contract check failed: see details below.

Full check log:
  ${CHECK_LOG}

Last 80 log lines:
EOF
tail -80 "${CHECK_LOG}"
exit 1
