#!/usr/bin/env bash
# Launch the FlowForm Docsys documentation MCP server.
#
# Exposes the deterministic docsys documentation tools (search_docs,
# get_document, get_related, get_task_context, get_impacted_docs,
# check_freshness, doc_health) over MCP stdio. It reuses the existing
# scripts/docs/docsys package; it does not reimplement anything.
#
# The server is standard-library only, so no virtualenv or dependency install
# is required — just a Python 3 interpreter.

set -euo pipefail

# Resolve the repository root from this script's location:
# tools/mcp/docsys_run.sh -> repo root is two levels up.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

# `docsys_run.sh tools` prints the exposed tool names (handy for verifying the
# server without an MCP client). It performs a single initialize/tools/list
# round-trip against the same entry point used in normal operation.
if [[ "${1:-}" == "tools" || "${1:-}" == "list-tools" ]]; then
    printf '%s\n%s\n' \
        '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
        | PYTHONPATH="$REPO_ROOT/scripts/docs" python3 -m docsys.mcp_server \
        | python3 -c 'import sys, json; [print(t["name"]) for t in json.loads(sys.stdin.readline())["result"]["tools"]]'
    exit 0
fi

exec env PYTHONPATH="$REPO_ROOT/scripts/docs" python3 -m docsys.mcp_server "$@"
