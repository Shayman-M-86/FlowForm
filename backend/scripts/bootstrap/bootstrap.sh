#!/usr/bin/env bash
set -e

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

uv sync --extra dev --extra test