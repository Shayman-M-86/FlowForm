#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"
source "$SCRIPT_DIR/.venv/bin/activate"
python "$SCRIPT_DIR/import_starlight_doc.py"
