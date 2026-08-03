#!/usr/bin/env bash
# Launch the FlowForm isolated documentation research MCP server.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

if [[ "${1:-}" == "tools" || "${1:-}" == "list-tools" ]]; then
    printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
        | PYTHONPATH="$REPO_ROOT/tools/docs" python3 -m docsys.research_mcp_server \
        | python3 -c 'import sys, json; [print(t["name"]) for t in json.loads(sys.stdin.readline())["result"]["tools"]]'
    exit 0
fi

exec env PYTHONPATH="$REPO_ROOT/tools/docs" python3 -m docsys.research_mcp_server "$@"
