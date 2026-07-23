#!/usr/bin/env bash
set -euo pipefail

# Thin executable wrapper for generate_secrets.py — see that file for docs.
#
#   scripts/secrets/generate-secrets.sh
#   scripts/secrets/generate-secrets.sh dev
#   scripts/secrets/generate-secrets.sh test --output-dir "$FLOWFORM_SECRET_DIR"
#
# Without --output-dir, files are routed to infra/env/<environment>/secrets.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/generate_secrets.py" "$@"
