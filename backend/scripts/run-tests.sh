#!/usr/bin/env bash
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
  echo "error: 'uv' not found on PATH. Install uv or run run-tests.py directly with Python 3.14+." >&2
  exit 1
fi

# --project pins uv to the backend environment no matter where we're invoked from.
exec env -u VIRTUAL_ENV uv run --project "$BACKEND_ROOT" --extra dev \
  python "$SCRIPT_DIR/run-tests.py" "$@"
