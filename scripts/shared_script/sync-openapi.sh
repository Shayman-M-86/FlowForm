#!/usr/bin/env bash
# Regenerate openapi.yaml from Python sources, then generate TypeScript types.
#
# Run from anywhere:
#   bash scripts/shared_script/sync-openapi.sh
#   bash scripts/shared_script/sync-openapi.sh --check

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ "${1:-}" == "--" ]]; then shift; fi

MODE="${1:-generate}"
if [[ "${MODE}" != "generate" && "${MODE}" != "--check" ]]; then
  echo "Usage: bash scripts/shared_script/sync-openapi.sh [--check]" >&2
  exit 2
fi

if [[ "${MODE}" == "--check" ]]; then
  echo "==> Checking OpenAPI spec and generated TypeScript drift..."
  cd "${REPO_ROOT}/frontend/apps/studio-app"
  pnpm run openapi:check

  cd "${REPO_ROOT}/frontend"
  pnpm exec redocly lint ../backend/openapi.yaml --config ../backend/.redocly.yaml

  cd "${REPO_ROOT}/frontend"
  pnpm run generate:types

  cd "${REPO_ROOT}"
  git diff --exit-code -- \
    frontend/apps/studio-app/src/api/generated/rbac.gen.ts \
    frontend/packages/schema/src/generated

  echo "==> Done."
  exit 0
fi

echo "==> Generating OpenAPI spec and all TypeScript types..."
cd "${REPO_ROOT}/frontend/apps/studio-app"
pnpm run openapi:generate

cd "${REPO_ROOT}/frontend"
pnpm exec redocly lint ../backend/openapi.yaml --config ../backend/.redocly.yaml

echo "==> Done."
