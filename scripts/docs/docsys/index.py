#!/usr/bin/env python3
"""Build the machine-readable documentation index.

Scans the documentation tree and emits a single JSON file,
``docs/90-generated/documentation-index.json``, that is the primary API every
other tool and AI agent uses instead of re-scanning ``docs/``. Each entry
captures the front matter, resolved code patterns, headings, and the wiki-link
graph for one document.

The index is deterministic and reproducible: given the same working tree it
produces byte-identical output (keys sorted, stable ordering), so it can be
committed and diffed. Run it from the repository root:

    python3 -m docsys index
"""

from __future__ import annotations

import json
from pathlib import Path

from . import gitutil
from .model import GENERATED_DIR, ROOT, DocSet, Document

INDEX_PATH = GENERATED_DIR / "documentation-index.json"

# Front-matter fields excluded from the flat `metadata` echo because they get
# dedicated, normalised fields in the entry.
_PROMOTED = {
    "title",
    "document_type",
    "status",
    "authority",
    "verified_against_commit",
    "tags",
    "related_code",
    "related_docs",
    "change_triggers",
    "exclusions",
    "code_confidence",
}


def _entry(doc: Document, docset: DocSet) -> dict:
    resolved_neighbours = [n.title for n in docset.neighbours(doc)]
    extra = {k: v for k, v in doc.front_matter.items() if k not in _PROMOTED}
    return {
        "path": doc.rel_path,
        "title": doc.title,
        "document_type": doc.document_type,
        "authority": doc.authority,
        "status": doc.status,
        "tags": sorted(doc.tags),
        "verified_against_commit": doc.verified_against_commit,
        "code_confidence": doc.code_confidence,
        "headings": list(doc.headings),
        # Raw declarations, as written by the author (relative to the doc).
        "related_code": list(doc.front_matter.get("related_code") or []),
        "change_triggers": list(doc.front_matter.get("change_triggers") or []),
        "exclusions": list(doc.front_matter.get("exclusions") or []),
        # Resolved repo-relative patterns, ready for matching against git.
        "related_code_resolved": list(doc.related_patterns),
        "change_triggers_resolved": list(doc.trigger_patterns),
        "exclusions_resolved": list(doc.exclusion_patterns),
        "related_docs": list(doc.related_docs),
        "wiki_links": list(doc.wiki_links),
        # Resolved undirected neighbour titles (links + backlinks).
        "neighbours": sorted(resolved_neighbours),
        "extra_metadata": extra,
    }


def build_index(docset: DocSet | None = None) -> dict:
    """Return the full index document as a JSON-serialisable dict."""
    docset = docset or DocSet.load()
    entries = [_entry(d, docset) for d in docset.docs]
    entries.sort(key=lambda e: e["path"])
    return {
        "schema": "flowform.docsys.index/1",
        "generated_by": "scripts/docs/docsys/index.py",
        "repo_head": gitutil.current_commit(),
        "document_count": len(entries),
        "documents": entries,
    }


def write_index(index: dict | None = None) -> Path:
    """Write the index to ``docs/90-generated/documentation-index.json``."""
    index = index or build_index()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2, sort_keys=False) + "\n")
    return INDEX_PATH


def load_index() -> dict | None:
    """Load a previously written index, or ``None`` if it does not exist."""
    if not INDEX_PATH.exists():
        return None
    try:
        return json.loads(INDEX_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def main(argv: list[str] | None = None) -> int:
    index = build_index()
    path = write_index(index)
    print(f"wrote {path.relative_to(ROOT)} ({index['document_count']} documents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
