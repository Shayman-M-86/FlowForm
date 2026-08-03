#!/usr/bin/env python3
"""Shared non-blocking Python quality hook for Codex and Claude."""

from __future__ import annotations

import subprocess
from pathlib import Path

from shared_hook_input import ROOT, read_hook_input


def _file_path(data: dict) -> str:
    tool_input = data.get("tool_input")
    if isinstance(tool_input, dict):
        value = tool_input.get("file_path")
        if value:
            return str(value)
    return str(data.get("file_path") or "")


def main() -> int:
    raw_path = _file_path(read_hook_input())
    if not raw_path.endswith(".py"):
        return 0

    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    backend = ROOT / "backend"
    try:
        path.resolve().relative_to(backend.resolve())
    except ValueError:
        return 0

    commands = (
        ["uv", "run", "--extra", "dev", "python", "-m", "py_compile", str(path)],
        [
            "uv",
            "run",
            "--extra",
            "dev",
            "ruff",
            "check",
            "--fix",
            "--unfixable",
            "F401,F811",
            str(path),
        ],
    )
    for command in commands:
        try:
            subprocess.run(
                command,
                cwd=backend,
                capture_output=True,
                check=False,
            )
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
