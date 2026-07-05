#!/usr/bin/env bash
# Run the integrity-rule / constraint-name cross-check from anywhere.
#
# Resolves its own location, so it works regardless of the current directory.
# It runs the Python checker through `uv` (with the dev extras for psycopg) from
# the backend project root. Any arguments are passed straight through, e.g.:
#
#     check-integrity-rule-constraints.sh --keep
#
# Requires: docker (spins up an ephemeral postgres:17) and uv.
set -euo pipefail

# Directory this script lives in, following symlinks — lets it be invoked via a
# symlink on PATH and still find the backend root and the Python script.
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
BACKEND_ROOT="$(cd "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "error: 'uv' not found on PATH. Install uv or run the .py directly with psycopg available." >&2
  exit 1
fi

# --project pins uv to the backend environment no matter where we're invoked from.
exec uv run --project "$BACKEND_ROOT" --extra dev \
  python "$SCRIPT_DIR/check_integrity_rule_constraints.py" "$@"
