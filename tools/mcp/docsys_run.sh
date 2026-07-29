#!/usr/bin/env bash
# Launch the FlowForm Docsys documentation MCP server.
#
# Exposes the bounded, read-only Docsys `find` and `read` tools over MCP stdio.
# The MCP adapter and CLI share the same Docsys request contracts.
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
        | PYTHONPATH="$REPO_ROOT/tools/docs" python3 -m docsys.mcp_server \
        | python3 -c 'import sys, json; [print(t["name"]) for t in json.loads(sys.stdin.readline())["result"]["tools"]]'
    exit 0
fi

exec env PYTHONPATH="$REPO_ROOT/tools/docs" python3 -m docsys.mcp_server "$@"
