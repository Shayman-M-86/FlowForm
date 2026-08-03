#!/usr/bin/env python3
"""Build the machine-readable documentation index.

Scans a documentation tree and emits a single JSON index in that tree's
generated-output directory. Each entry
captures the front matter, resolved code patterns, headings, and the wiki-link
graph for one document.

The index is deterministic and reproducible: given the same working tree it
produces byte-identical output (keys sorted, stable ordering), so it can be
committed and diffed. Run it from the repository root:

    tools/bin/docsys index
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..core import gitutil
from ..core.model import ROOT, DocSet, Document, generated_dir_for, resolve_docs_root

INDEX_PATH = generated_dir_for(resolve_docs_root()) / "documentation-index.json"

# Front-matter fields excluded from the flat `metadata` echo because they get
# dedicated, normalised fields in the entry.
_PROMOTED = {
    "title",
    "document_type",
    "status",
    "authority",
    "verified_evidence_digest",
    "last_edited",
    "tags",
    "related_code",
    "related_docs",
    "change_triggers",
    "exclusions",
    "code_confidence",
}


def _entry(doc: Document, docset: DocSet) -> dict:
    resolved_neighbours = [n.title for n in docset.neighbours(doc)]
    parent = docset.inferred_parent(doc)
    extra = {k: v for k, v in doc.front_matter.items() if k not in _PROMOTED}
    return {
        "path": doc.rel_path,
        "title": doc.title,
        "document_type": doc.document_type,
        "authority": doc.authority,
        "status": doc.status,
        "collection": doc.collection,
        "is_folder_head": doc.is_folder_head,
        "parent": parent.title if parent else None,
        "children": [child.title for child in docset.children(doc)],
        "tags": sorted(doc.tags),
        "verified_evidence_digest": doc.verified_evidence_digest,
        "last_edited": doc.last_edited,
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
        "generated_by": "tools/flowform_tools/docsys/commands/index.py",
        "repo_head": gitutil.current_commit(),
        "document_count": len(entries),
        "documents": entries,
    }


def write_index(
    index: dict | None = None, docs_dir: Path | None = None
) -> Path:
    """Write the index to the selected root's generated-output directory."""
    docs_dir = resolve_docs_root(docs_dir)
    index = index or build_index(DocSet.load(docs_dir))
    path = generated_dir_for(docs_dir) / "documentation-index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2, sort_keys=False) + "\n")
    return path


def load_index(docs_dir: Path | None = None) -> dict | None:
    """Load a previously written index, or ``None`` if it does not exist."""
    path = generated_dir_for(resolve_docs_root(docs_dir)) / "documentation-index.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docsys index")
    parser.add_argument(
        "--docs-root",
        default=None,
        help="documentation root (default: active root)",
    )
    args = parser.parse_args(argv)
    docs_dir = resolve_docs_root(args.docs_root)
    index = build_index(DocSet.load(docs_dir))
    path = write_index(index, docs_dir)
    print(f"wrote {path.relative_to(ROOT)} ({index['document_count']} documents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
