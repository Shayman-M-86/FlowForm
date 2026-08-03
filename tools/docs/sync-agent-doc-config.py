#!/usr/bin/env python3
"""Synchronize the small agent-facing documentation workflow mirrors."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ("flowform-doc-context", "flowform-doc-verification")


@dataclass(frozen=True)
class Mirror:
    target: Path
    content: str


def _section(text: str, heading: str) -> str:
    start = text.index(f"{heading}\n")
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end < 0 else text[start:end]


def _replace_section(text: str, heading: str, replacement: str) -> str:
    current = _section(text, heading)
    return text.replace(current, replacement, 1)


def mirrors() -> list[Mirror]:
    result = []
    for name in SKILLS:
        source = ROOT / ".agents" / "skills" / name / "SKILL.md"
        target = ROOT / ".claude" / "skills" / name / "SKILL.md"
        result.append(Mirror(target=target, content=source.read_text()))
    agents_guide = (ROOT / "AGENTS.md").read_text()
    claude_path = ROOT / "CLAUDE.md"
    result.append(
        Mirror(
            target=claude_path,
            content=_replace_section(
                claude_path.read_text(),
                "## Documentation",
                _section(agents_guide, "## Documentation"),
            ),
        )
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check or update shared Claude documentation workflow mirrors."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report drift")
    mode.add_argument("--write", action="store_true", help="update drifted mirrors")
    args = parser.parse_args(argv)

    changed = [
        mirror
        for mirror in mirrors()
        if not mirror.target.exists() or mirror.target.read_text() != mirror.content
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
