#!/usr/bin/env python3
"""Validate links between documentation files.

Checks every Markdown file under docs/ for:
- Obsidian [[wiki links]] (with optional |display text) that resolve,
  case-insensitively, to a note filename or shortest unique note path
- relative Markdown links whose targets do not exist on disk

Code fences and inline code spans are ignored, so conventions can be shown as
literal examples. Exits 0 on success and 1 when validation issues are found.
Dependency-free by design; see
docs/project-knowledge/engineering-practices/documentation/documentation-model.md.
"""

from __future__ import annotations

import re

from flowform_tools.docsys.core.model import (
    DOCS,
    body_after_front_matter,
    is_inert_archive_path,
    strip_code,
)
from flowform_tools.paths import ROOT

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
WIKI_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")


def main(argv: list[str] | None = None) -> int:
    """Validate documentation links and report any issues."""
    issues: list[str] = []

    # Match Obsidian's shortest-path convention: a unique filename stem is
    # enough; duplicate stems use their path relative to docs/ (without .md).
    paths = sorted(path for path in DOCS.rglob("*.md") if not is_inert_archive_path(path))
    stem_counts: dict[str, int] = {}
    for path in paths:
        key = path.stem.casefold()
        stem_counts[key] = stem_counts.get(key, 0) + 1

    targets = {}
    for path in paths:
        target = (path.stem if stem_counts[path.stem.casefold()] == 1 else
                  path.relative_to(DOCS).with_suffix("").as_posix())
        targets[target.casefold()] = path.relative_to(ROOT)

    for path in paths:
        rel = path.relative_to(ROOT)
        body = strip_code(body_after_front_matter(path.read_text(errors="replace")))

        for target in WIKI_LINK.findall(body):
            if target.strip().casefold() not in targets:
                issues.append(f"{rel}: unresolved wiki link [[{target}]]")

        for link in MD_LINK.findall(body):
            if "://" in link or link.startswith(("#", "mailto:")):
                continue
            target = link.split("#")[0]
            if target and not (path.parent / target).resolve().exists():
                issues.append(f"{rel}: broken link {link}")

    for issue in issues:
        print(issue)
    print(f"checked links against {len(targets)} Obsidian note targets: "
          f"{'OK' if not issues else f'{len(issues)} issue(s)'}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
