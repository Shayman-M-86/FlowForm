#!/usr/bin/env python3
"""Shared input adapter for FlowForm agent hooks."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read_hook_input() -> dict:
    """Read hook input from whichever channel the calling agent uses.

    Claude Code passes a JSON object on stdin. Codex (per this repo's existing
    hooks) exposes the payload via the ``CLAUDE_TOOL_INPUT`` environment
    variable and may leave stdin empty. This adapter accepts either, so the
    same hook scripts work for both agents.
    """
    # Prefer stdin JSON (Claude Code, and any agent that supplies it).
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

    # Fall back to the env-var payload used by Codex hooks in this repo.
    for var in ("CLAUDE_TOOL_INPUT", "CODEX_HOOK_INPUT", "CODEX_TOOL_INPUT"):
        env_raw = os.environ.get(var)
        if env_raw:
            try:
                data = json.loads(env_raw)
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, ValueError):
                continue
    return {}
