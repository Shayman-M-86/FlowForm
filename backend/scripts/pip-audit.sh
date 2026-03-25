#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Detect OS and set correct python path
if [[ "$OS" == "Windows_NT" ]]; then
    PYTHON_PATH_1="$PROJECT_ROOT/.venv/Scripts/python.exe"
else
    PYTHON_PATH_1="$PROJECT_ROOT/.venv/bin/python"
fi

# Validate path
if [[ ! -f "$PYTHON_PATH_1" ]]; then
    echo "❌ Python executable not found at $PYTHON_PATH_1"
    exit 1
fi

echo "Using Python executable at $PYTHON_PATH_1"

# Set for pip-audit (optional but fine)
export PIPAPI_PYTHON_LOCATION="$PYTHON_PATH_1"

# Run pip-audit correctly (module name uses underscore)
"$PYTHON_PATH_1" -m pip_audit