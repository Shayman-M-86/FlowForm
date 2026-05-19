#!/usr/bin/env bash
# Launch the FlowForm dev MCP server from anywhere.
#
# Optional: place a `.env` file next to this script with KEY=VALUE lines
# (e.g. FLOWFORM_DEV_TOKEN=...) and it will be sourced automatically.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
fi

cd "$SCRIPT_DIR"

# `run.sh login` triggers a fresh device-flow login and exits. Useful if the
# cached refresh token is revoked or you want to switch accounts.
if [[ "${1:-}" == "login" ]]; then
    exec uv run --project "$SCRIPT_DIR" python auth.py login
fi

exec uv run --project "$SCRIPT_DIR" python flowform_dev.py "$@"
