#!/usr/bin/env python3
"""Validate documentation front matter and knowledge-network metadata.

Checks every Markdown file under docs/ for:
- required front-matter keys (title, document_type, status, authority,
  verified_against_commit, aliases, related_code, related_docs)
- an allowed status value
- globally unique titles (case-insensitive), since wiki links resolve by title
- an Obsidian alias matching each document title
- tags drawn only from the controlled vocabulary in the documentation model
- related_docs entries that resolve to an existing document title
- optional tooling fields, when present, having valid shapes: change_triggers
  and exclusions must be lists; code_confidence must be high/medium/low

Exits 0 on success and 1 when validation issues are found. Dependency-free by
design; see docs/00-overview/documentation-model.md for the conventions.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

REQUIRED = ["title", "document_type", "status", "authority",
            "verified_against_commit", "aliases", "related_code", "related_docs"]
ALLOWED_STATUS = {"scaffold", "draft", "verified"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
# Optional tooling fields (consumed by scripts/docs/docsys/): related_code may
# use directories and globs; change_triggers/exclusions extend or subtract the
# matched code set; code_confidence weights impact/freshness. See the
# documentation model for the contract.
LIST_FIELDS = {"aliases", "change_triggers", "exclusions"}
TAG_VOCABULARY = {"backend", "frontend", "infrastructure", "security",
                  "configuration", "ci-cd", "tooling", "meta"}

issues = []
docs = {}  # path -> parsed front matter


def parse_front_matter(path, text):
    """Parse the canonical front-matter shape used across docs/."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm, current_list = {}, None
    for line in text[3:end].splitlines():
        if not line.strip():
            continue
        item = re.match(r'\s+-\s+"?([^"]*)"?\s*$', line)
        if item and current_list is not None:
            fm[current_list].append(item.group(1))
            continue
        kv = re.match(r"([A-Za-z_-]+):\s*(.*)$", line)
        if not kv:
            issues.append(f"{path}: unparseable front-matter line: {line!r}")
            continue
        key, value = kv.group(1), kv.group(2).strip()
        if value == "":
            fm[key], current_list = [], key
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fm[key] = [v.strip().strip('"') for v in inner.split(",")] if inner else []
            current_list = None
        else:
            fm[key], current_list = value.strip('"'), None
    return fm


for path in sorted(DOCS.rglob("*.md")):
    rel = path.relative_to(ROOT)
    fm = parse_front_matter(rel, path.read_text(errors="replace"))
    if fm is None:
        issues.append(f"{rel}: missing or unterminated front matter")
        continue
    docs[rel] = fm
    for key in REQUIRED:
        if key not in fm:
            issues.append(f"{rel}: missing front-matter key '{key}'")
    status = fm.get("status")
    if status is not None and status not in ALLOWED_STATUS:
        issues.append(f"{rel}: status '{status}' not in {sorted(ALLOWED_STATUS)}")
    for tag in fm.get("tags", []):
        if tag not in TAG_VOCABULARY:
            issues.append(f"{rel}: tag '{tag}' not in controlled vocabulary "
                          f"{sorted(TAG_VOCABULARY)}")
    for field in LIST_FIELDS:
        if field in fm and not isinstance(fm[field], list):
            issues.append(f"{rel}: optional field '{field}' must be a list")
    confidence = fm.get("code_confidence")
    if confidence is not None and confidence not in ALLOWED_CONFIDENCE:
        issues.append(f"{rel}: code_confidence '{confidence}' not in "
                      f"{sorted(ALLOWED_CONFIDENCE)}")

# Titles must be unique because wiki links resolve by title.
by_title = {}
for rel, fm in docs.items():
    title = fm.get("title")
    if not isinstance(title, str) or not title:
        issues.append(f"{rel}: missing or empty title")
        continue
    key = title.casefold()
    if key in by_title:
        issues.append(f"{rel}: duplicate title '{title}' (also in {by_title[key]})")
    else:
        by_title[key] = rel

    aliases = fm.get("aliases", [])
    if isinstance(aliases, list) and title.casefold() not in {
            alias.casefold() for alias in aliases}:
        issues.append(f"{rel}: aliases must include the document title '{title}'")

# related_docs entries must resolve to existing titles.
for rel, fm in docs.items():
    related = fm.get("related_docs", [])
    if isinstance(related, str):
        issues.append(f"{rel}: related_docs must be a list")
        continue
    for entry in related:
        if entry.casefold() not in by_title:
            issues.append(f"{rel}: related_docs entry '{entry}' does not match any title")
        elif entry.casefold() == str(fm.get("title", "")).casefold():
            issues.append(f"{rel}: related_docs must not reference the document itself")

for issue in issues:
    print(issue)
print(f"checked {len(docs)} documents: "
      f"{'OK' if not issues else f'{len(issues)} issue(s)'}")
raise SystemExit(1 if issues else 0)
