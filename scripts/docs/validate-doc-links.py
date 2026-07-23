#!/usr/bin/env python3
"""Validate links between documentation files.

Checks every Markdown file under docs/ for:
- Obsidian [[wiki links]] (with optional |display text) that resolve,
  case-insensitively, to a note filename or shortest unique note path
- relative Markdown links whose targets do not exist on disk

Code fences and inline code spans are ignored, so conventions can be shown as
literal examples. Exits 0 on success and 1 when validation issues are found.
Dependency-free by design; see docs/00-overview/documentation-model.md.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
WIKI_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
CODE_FENCE = re.compile(r"^```.*?^```", re.M | re.S)
CODE_SPAN = re.compile(r"`[^`\n]*`")
issues = []

# Match Obsidian's shortest-path convention: a unique filename stem is enough;
# duplicate stems use their path relative to docs/ (without the .md suffix).
paths = sorted(DOCS.rglob("*.md"))
stem_counts = {}
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
    body = path.read_text(errors="replace")
    if body.startswith("---") and (end := body.find("\n---", 3)) != -1:
        body = body[end + 4:]
    body = CODE_SPAN.sub("", CODE_FENCE.sub("", body))

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
raise SystemExit(1 if issues else 0)
