"""Shared dependency-free CLI, pagination, and Markdown helpers."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any, TypeVar

T = TypeVar("T")


def add_output_args(
    parser: argparse.ArgumentParser, *, default_limit: int
) -> None:
    """Add the common bounded-output arguments to a command parser."""
    parser.add_argument("--limit", type=int, default=default_limit)
    parser.add_argument("--all", action="store_true", dest="show_all")
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")


def paginate(
    items: Sequence[T], *, limit: int, show_all: bool
) -> tuple[list[T], int, bool]:
    """Return a bounded page plus stable envelope counts."""
    if limit < 1:
        raise ValueError("--limit must be at least 1")
    total = len(items)
    shown = list(items) if show_all else list(items[:limit])
    return shown, total, len(shown) < total


def envelope(
    schema: str,
    items: Sequence[Any],
    *,
    total: int | None = None,
    **metadata: Any,
) -> dict[str, Any]:
    """Build the standard Docsys bounded-output JSON envelope."""
    shown = list(items)
    item_total = len(shown) if total is None else total
    return {
        "schema": schema,
        **metadata,
        "total": item_total,
        "returned": len(shown),
        "truncated": len(shown) < item_total,
        "items": shown,
    }


def markdown_cell(value: object) -> str:
    """Escape table syntax and wiki-link-like text inside a Markdown cell."""
    text = str(value).replace("|", "\\|")
    return text.replace("[[", "&#91;&#91;").replace("]]", "&#93;&#93;")


def markdown_table(headers: Sequence[object], rows: Sequence[Sequence[object]]) -> str:
    """Render a Markdown table whose data cells cannot corrupt its structure."""
    if not rows:
        return "_None._\n"
    out = ["| " + " | ".join(str(header) for header in headers) + " |"]
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    out.extend(
        "| " + " | ".join(markdown_cell(cell) for cell in row) + " |"
        for row in rows
    )
    return "\n".join(out) + "\n"
