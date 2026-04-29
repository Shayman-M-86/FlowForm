#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required to compile backend requirements and run pip-audit." >&2
    exit 1
fi

REQUIREMENTS_FILE="$(mktemp "${TMPDIR:-/tmp}/flowform-pip-audit-requirements.XXXXXX.txt")"
cleanup() {
    rm -f "$REQUIREMENTS_FILE"
}
trap cleanup EXIT INT TERM

echo "Compiling backend requirements for pip-audit..."
uv pip compile pyproject.toml --extra dev --extra test -o "$REQUIREMENTS_FILE"

echo "Running pip-audit..."
uvx pip-audit -r "$REQUIREMENTS_FILE" "$@"
