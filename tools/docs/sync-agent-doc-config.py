#!/usr/bin/env python3
"""Synchronize the small agent-facing documentation workflow mirrors."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ("flowform-doc-context", "flowform-doc-verification")


@dataclass(frozen=True)
class Mirror:
    target: Path
    content: str


def _front_matter_value(text: str, key: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    prefix = f"{key}:"
    for line in text[4:end].splitlines():
        if line.startswith(prefix):
            return line.partition(":")[2].strip().strip("\"'")
    return None


def _claude_maintainer() -> str:
    source = ROOT / ".codex" / "agents" / "docs-maintainer.toml"
    target = ROOT / ".claude" / "agents" / "docs-maintainer.md"
    data = tomllib.loads(source.read_text())
    current = target.read_text() if target.exists() else ""
    model = _front_matter_value(current, "model") or "sonnet"
    instructions = str(data["developer_instructions"]).strip()
    return (
        "---\n"
        f"name: {data['name']}\n"
        f"description: {data['description']}\n"
        f"model: {model}\n"
        "---\n\n"
        f"{instructions}\n"
    )


def mirrors() -> list[Mirror]:
    result = []
    for name in SKILLS:
        source = ROOT / ".agents" / "skills" / name / "SKILL.md"
        target = ROOT / ".claude" / "skills" / name / "SKILL.md"
        result.append(Mirror(target=target, content=source.read_text()))
    result.append(
        Mirror(
            target=ROOT / ".claude" / "agents" / "docs-maintainer.md",
            content=_claude_maintainer(),
        )
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check or update Claude documentation workflow mirrors."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report drift")
    mode.add_argument("--write", action="store_true", help="update drifted mirrors")
    args = parser.parse_args(argv)

    changed = [
        mirror
        for mirror in mirrors()
        if not mirror.target.exists()
        or mirror.target.read_text() != mirror.content
    ]
    action = "DIFFERS" if args.check else "UPDATED"
    for mirror in changed:
        print(f"{action}: {mirror.target.relative_to(ROOT)}")

    if args.write:
        for mirror in changed:
            mirror.target.parent.mkdir(parents=True, exist_ok=True)
            mirror.target.write_text(mirror.content)
        print(f"write: {len(changed)} file(s) updated")
        return 0

    print(f"check: {len(changed)} file(s) differ")
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
