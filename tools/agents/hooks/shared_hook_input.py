#!/usr/bin/env python3
"""Shared input adapter for FlowForm agent hooks."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read_hook_input() -> dict:
    """Read hook input from stdin or a supported agent environment variable."""
    raw = ""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
    except (OSError, ValueError):
        raw = ""
    if raw.strip():
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass

    for variable in ("CLAUDE_TOOL_INPUT", "CODEX_HOOK_INPUT", "CODEX_TOOL_INPUT"):
        value = os.environ.get(variable)
        if value:
            try:
                data = json.loads(value)
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, ValueError):
                continue
    return {}
