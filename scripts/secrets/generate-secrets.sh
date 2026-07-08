#!/usr/bin/env bash
set -euo pipefail

# Thin executable wrapper for generate_secrets.py — see that file for docs.
#
#   scripts/infra/generate-secrets.sh dev
#   scripts/infra/generate-secrets.sh test --output-dir "$FLOWFORM_SECRET_DIR"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/generate_secrets.py" "$@"
