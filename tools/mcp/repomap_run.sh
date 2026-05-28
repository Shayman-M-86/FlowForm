#!/usr/bin/env bash
# Launch the FlowForm repomap MCP server from anywhere.
#
# This server orchestrates iterative repo summarisation — Claude reads each
# path from .claude/repomap-config.json and saves summaries back to
# .claude/repomap.md via the MCP tools.
#
# It shares the same venv and dependencies as the flowform-dev MCP server.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
fi

cd "$SCRIPT_DIR"

if [[ "${1:-}" == "tools" || "${1:-}" == "list-tools" ]]; then
    exec uv run --project "$SCRIPT_DIR" fastmcp list --command "bash $SCRIPT_DIR/repomap_run.sh"
fi

if [[ "${1:-}" == "tool-schemas" || "${1:-}" == "tools-schema" ]]; then
    exec uv run --project "$SCRIPT_DIR" fastmcp list --command "bash $SCRIPT_DIR/repomap_run.sh" --input-schema
fi

exec uv run --project "$SCRIPT_DIR" python repomap.py "$@"
