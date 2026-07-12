#!/usr/bin/env python3
"""Validate links between documentation files.

Checks every Markdown file under docs/ for:
- [[wiki links]] (with optional |display alias) that resolve, case-insensitively,
  to the front-matter title of a document under docs/
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
TITLE = re.compile(r"^title:\s*(.+?)\s*$", re.M)

issues = []

# Index titles: wiki links resolve by title, never by path.
titles = {}
for path in DOCS.rglob("*.md"):
    text = path.read_text(errors="replace")
    if text.startswith("---") and (end := text.find("\n---", 3)) != -1:
        if m := TITLE.search(text[3:end]):
            titles[m.group(1).strip('"').casefold()] = path.relative_to(ROOT)

for path in sorted(DOCS.rglob("*.md")):
    rel = path.relative_to(ROOT)
    body = path.read_text(errors="replace")
    if body.startswith("---") and (end := body.find("\n---", 3)) != -1:
        body = body[end + 4:]
    body = CODE_SPAN.sub("", CODE_FENCE.sub("", body))

    for target in WIKI_LINK.findall(body):
        if target.strip().casefold() not in titles:
            issues.append(f"{rel}: unresolved wiki link [[{target}]]")

    for link in MD_LINK.findall(body):
        if "://" in link or link.startswith(("#", "mailto:")):
            continue
        target = link.split("#")[0]
        if target and not (path.parent / target).resolve().exists():
            issues.append(f"{rel}: broken link {link}")

for issue in issues:
    print(issue)
print(f"checked links against {len(titles)} titles: "
      f"{'OK' if not issues else f'{len(issues)} issue(s)'}")
raise SystemExit(1 if issues else 0)
