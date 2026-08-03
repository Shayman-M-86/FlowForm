"""CLI entry point for source-backed Docsys research."""

from __future__ import annotations

import argparse
import json
from typing import Any

from ..research import (
    DEPTHS,
    PROVIDERS,
    ResearchRequest,
    ResearchRuntimeError,
    run_research,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docsys research",
        description="Answer one FlowForm question with local Claude Code or Codex.",
    )
    parser.add_argument("question", help="exact research question")
    parser.add_argument(
        "--depth",
        choices=sorted(DEPTHS),
        default="quick",
        help="quick or thorough model profile (default: quick)",
    )
    parser.add_argument("--model", help="override the selected provider model")
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        default="auto",
        help="research provider (default: Claude, with Codex fallback)",
    )
    parser.add_argument("--scope", help="repository-relative search scope")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format (default: text)",
    )
    return parser


def _print_text(result: dict[str, Any]) -> None:
    print(result["answer"])
    print()
    print(
        f"confidence: {result['confidence']} | basis: {result['basis']} | "
        f"provider: {result['runtime']['provider']} | "
        f"model: {result['runtime']['model']}"
    )
    for finding in result["findings"]:
        print(f"- {finding['claim']}")
        for source in finding["sources"]:
            print(
                f"  {source['path']}:{source['start_line']}-{source['end_line']} "
                f"({source['kind']})"
            )
    for heading, key in (
        ("contradictions", "contradictions"),
        ("unresolved", "unresolved"),
    ):
        if result[key]:
            print(f"{heading}:")
            for item in result[key]:
                print(f"- {item}")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = run_research(
            ResearchRequest(
                question=args.question,
                depth=args.depth,
                model=args.model,
                scope=args.scope,
                provider=args.provider,
            )
        )
    except (ValueError, ResearchRuntimeError) as error:
        parser.error(str(error))

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
