#!/usr/bin/env python3
"""Machine-readable Docsys and spawned-research capability inventory."""

from __future__ import annotations

import argparse
import json
import shutil

from .command_catalog import DOCSYS_COMMANDS, RESEARCH_CLI_TOOLS
from .model import ROOT


def _available(executable: str) -> tuple[bool, str | None]:
    if "/" in executable:
        path = ROOT / executable
        return path.is_file(), str(path) if path.is_file() else None
    resolved = shutil.which(executable)
    return resolved is not None, resolved


def _research_tool(tool: dict) -> dict:
    available, resolved_path = _available(tool["executable"])
    return {
        **tool,
        "available": available,
        "resolved_path": resolved_path,
    }


def inventory() -> dict:
    return {
        "schema": "flowform.docsys.capabilities/1",
        "docsys_commands": [
            {
                "name": name,
                **{
                    key: spec[key]
                    for key in ("description", "access", "write_controls")
                    if key in spec
                },
            }
            for name, spec in DOCSYS_COMMANDS.items()
        ],
        "research_session": {
            "enforcement": "prompt-policy-and-read-only-sandbox",
            "commands": [_research_tool(tool) for tool in RESEARCH_CLI_TOOLS],
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docsys capabilities",
        description="List Docsys commands and spawned-research CLI tools.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format (default: text)",
    )
    return parser


def _print_text(payload: dict) -> None:
    print("Docsys commands:")
    for command in payload["docsys_commands"]:
        print(f"- {command['name']} [{command['access']}]: {command['description']}")
    print("Research CLI tools:")
    for tool in payload["research_session"]["commands"]:
        status = "ready" if tool["available"] else "missing"
        print(f"- {tool['executable']} [{status}]: {tool['usage']}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = inventory()
    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _print_text(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
