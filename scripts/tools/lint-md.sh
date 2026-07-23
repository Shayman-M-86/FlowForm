#!/usr/bin/env bash
# Lint (or auto-fix with --fix) all markdown in the repo.
# Config is defined inline here rather than in a separate .markdownlint-cli2.jsonc file.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CONFIG_FILE="$(mktemp -t markdownlint-cli2-config.XXXXXX.jsonc)"
trap 'rm -f "$CONFIG_FILE"' EXIT

cat > "$CONFIG_FILE" << 'JSON'
{
  "config": {
    "default": true,
    "MD013": false,
    "MD060": false
  },
  "ignores": [
    "**/node_modules/**",
    "**/.venv/**",
    "**/dist/**",
    "**/build/**"
  ]
}
JSON

exec npx markdownlint-cli2 --config "$CONFIG_FILE" "$@" "**/*.md"
