#!/usr/bin/env bash
# Regenerate backend/openapi.yaml from the current Python sources.
#
# Run from anywhere — the script resolves its own location.
#
# Examples:
#   bash backend/scripts/export-openapi.sh
#   bash backend/scripts/export-openapi.sh --check   # CI drift check
#   bash backend/scripts/export-openapi.sh --output /tmp/snapshot.yaml

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${BACKEND_DIR}"
exec uv run --extra dev python -m app.openapi.export "$@"
