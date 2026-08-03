#!/usr/bin/env python3
"""FlowForm documentation tooling."""

from __future__ import annotations

import importlib
import sys

_COMMANDS = {
    "find": ("docsys.query", "find a small set of relevant documents"),
    "read": ("docsys.retrieve", "read one exact document or section"),
    "research": ("docsys.research", "answer one question in a fresh Codex session"),
    "impact": ("docsys.impact", "find documentation affected by code changes"),
    "freshness": ("docsys.freshness", "check implementation evidence freshness"),
    "health": ("docsys.health", "summarize documentation health"),
    "debt": ("docsys.debt", "inspect documentation maintenance debt"),
    "validate": ("docsys.validate", "validate documentation structure"),
    "index": ("docsys.index", "regenerate the documentation index"),
    "evidence": ("docsys.evidence", "check or promote verification evidence"),
}


def _print_help() -> None:
    print("usage: docsys COMMAND [OPTIONS]")
    print()
    print("Focused documentation discovery and maintenance.")
    print()
    print("commands:")
    width = max(len(command) for command in _COMMANDS)
    for command, (_, description) in _COMMANDS.items():
        print(f"  {command:<{width}}  {description}")
    print()
    print("Run 'docsys COMMAND --help' for command options.")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        _print_help()
        return 0

    command, rest = args[0], args[1:]
    target = _COMMANDS.get(command)
    if target is None:
        print(f"unknown command: {command}", file=sys.stderr)
        print("Run 'docsys --help' for available commands.", file=sys.stderr)
        return 2

    module = importlib.import_module(target[0])
    return module.main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
