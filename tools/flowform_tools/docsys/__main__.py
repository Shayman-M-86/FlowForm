#!/usr/bin/env python3
"""FlowForm documentation tooling."""

from __future__ import annotations

import importlib
import sys

from .command_catalog import DOCSYS_COMMANDS


def _print_help() -> None:
    print("usage: docsys COMMAND [OPTIONS]")
    print()
    print("Focused documentation discovery and maintenance.")
    print()
    print("commands:")
    width = max(len(command) for command in DOCSYS_COMMANDS)
    for command, spec in DOCSYS_COMMANDS.items():
        print(f"  {command:<{width}}  {spec['description']}")
    print()
    print("Run 'docsys COMMAND --help' for command options.")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        _print_help()
        return 0

    command, rest = args[0], args[1:]
    target = DOCSYS_COMMANDS.get(command)
    if target is None:
        print(f"unknown command: {command}", file=sys.stderr)
        print("Run 'docsys --help' for available commands.", file=sys.stderr)
        return 2

    module = importlib.import_module(target["module"])
    return module.main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
