#!/usr/bin/env python3
"""Single entry point for the documentation tooling: ``python3 -m docsys``.

Subcommands map to the focused tools in this package:

    index       (re)build docs/90-generated/documentation-index.json
    impact      report documentation impacted by code changes
    freshness   classify documents against their verified commit
    query       ranked deterministic search over documentation
    context     assemble minimal task/change context
    health      regenerate the documentation health report + dashboard
    propose     scaffold reviewable, agent-assisted update proposals

Each subcommand also runs standalone (``python3 -m docsys.impact ...``); this
dispatcher just gives agents and humans one memorable command.
"""

from __future__ import annotations

import sys

_COMMANDS = {
    "index": "docsys.index",
    "impact": "docsys.impact",
    "freshness": "docsys.freshness",
    "query": "docsys.query",
    "context": "docsys.context",
    "health": "docsys.health",
    "propose": "docsys.propose",
}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("commands:", ", ".join(_COMMANDS))
        return 0
    cmd, rest = argv[0], argv[1:]
    module_name = _COMMANDS.get(cmd)
    if not module_name:
        print(f"unknown command: {cmd}")
        print("commands:", ", ".join(_COMMANDS))
        return 2
    import importlib

    module = importlib.import_module(module_name)
    return module.main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
