#!/usr/bin/env bash
# Regenerate openapi.yaml from Python sources, then generate TypeScript types.
#
# Run from anywhere:
#   bash scripts/shared_script/sync-openapi.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "==> Exporting OpenAPI spec from backend..."
bash "${REPO_ROOT}/backend/scripts/export-openapi.sh"

echo "==> Generating TypeScript types for studio-app..."
cd "${REPO_ROOT}/frontend/apps/studio-app"
npm run openapi:types

echo "==> Done."
