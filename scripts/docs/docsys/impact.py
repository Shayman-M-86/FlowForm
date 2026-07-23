#!/usr/bin/env python3
"""Documentation impact detection.

Given a set of changed files (from a git diff), map them onto documents via
each document's ``related_code`` / ``change_triggers`` patterns, rank how
confident the match is, and explain why each document was selected. The output
identifies documentation that *may* need review — it never modifies anything.

Confidence heuristic (deterministic):

- ``high``    an exact file match, or a change to a document's own verified
              code paths for a ``verified``/``draft`` document
- ``medium``  a directory or glob match to ``related_code``
- ``low``     matched only through a broader ``change_triggers`` pattern, or a
              wide directory prefix

Run it from the repository root:

    python3 -m docsys impact                 # working tree vs HEAD
    python3 -m docsys impact --base origin/main
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import gitutil
from .model import DocSet, Document, pattern_matches

_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Match:
    """One (document, changed-file) match with an explanation."""

    file: str
    pattern: str
    source: str  # "related_code" | "change_triggers"
    kind: str  # "exact" | "directory" | "glob"


@dataclass
class ImpactedDoc:
    doc: Document
    matches: list[Match] = field(default_factory=list)
    confidence: str = "low"
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "path": self.doc.rel_path,
            "title": self.doc.title,
            "document_type": self.doc.document_type,
            "status": self.doc.status,
            "verified_against_commit": self.doc.verified_against_commit,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "matched_files": sorted({m.file for m in self.matches}),
            "matches": [
                {
                    "file": m.file,
                    "pattern": m.pattern,
                    "source": m.source,
                    "kind": m.kind,
                }
                for m in self.matches
            ],
        }


def _match_kind(pattern: str) -> str:
    if pattern.endswith("/"):
        return "directory"
    if any(ch in pattern for ch in "*?["):
        return "glob"
    return "exact"


def _confidence_for(doc: Document, matches: list[Match]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    best = "low"
    kinds = {m.kind for m in matches}
    sources = {m.source for m in matches}

    if "exact" in kinds and "related_code" in sources:
        best = "high"
        reasons.append("a file named directly in related_code changed")
    elif {"directory", "glob"} & kinds and "related_code" in sources:
        best = "medium"
        reasons.append("a directory or glob in related_code changed")
    elif "change_triggers" in sources:
        best = "low"
        reasons.append("only a change_triggers pattern matched")

    # Only an exact-file match earns "high". Broad directory/glob matches stay
    # "medium" even for verified/draft docs: a change somewhere under
    # backend/app/ is not strong evidence that a specific architecture document
    # is now wrong, and promoting it floods any finish-time gate with the whole
    # architecture section. Demotions below still apply — they reduce noise.
    if doc.status == "scaffold":
        reasons.append("document is a scaffold; review value is lower")
        if best == "high":
            best = "medium"

    if doc.code_confidence == "low":
        reasons.append("code_confidence is 'low', weakening this match")
        if best == "high":
            best = "medium"

    return best, reasons


def detect_impact(
    changed_files: list[str], docset: DocSet | None = None
) -> list[ImpactedDoc]:
    """Return impacted documents, most confident first.

    Only documents that own at least one changed file are returned. Generated
    documents are included when their sources change (agents may want to
    regenerate them), but callers can filter on ``document_type``.
    """
    docset = docset or DocSet.load()
    impacted: list[ImpactedDoc] = []
    for doc in docset.docs:
        matches: list[Match] = []
        for f in changed_files:
            if any(pattern_matches(x, f) for x in doc.exclusion_patterns):
                continue
            for pattern in doc.related_patterns:
                if pattern_matches(pattern, f):
                    matches.append(
                        Match(f, pattern, "related_code", _match_kind(pattern))
                    )
            for pattern in doc.trigger_patterns:
                if pattern_matches(pattern, f):
                    matches.append(
                        Match(f, pattern, "change_triggers", _match_kind(pattern))
                    )
        if not matches:
            continue
        confidence, reasons = _confidence_for(doc, matches)
        impacted.append(ImpactedDoc(doc, matches, confidence, reasons))

    impacted.sort(
        key=lambda i: (_ORDER[i.confidence], -len(i.matches), i.doc.rel_path)
    )
    return impacted


def impact_report(
    base: str | None = None,
    head: str | None = None,
    docset: DocSet | None = None,
) -> dict:
    """Build a full impact report for a git range (or the working tree)."""
    diff = gitutil.changed_files(base, head)
    # Documentation edits themselves are reported separately so a reviewer can
    # see whether impacted docs were already touched in the same change.
    code_changes = [f for f in diff.files if not f.startswith("docs/")]
    doc_changes = [f for f in diff.files if f.startswith("docs/")]
    impacted = detect_impact(code_changes, docset)

    changed_doc_paths = set(doc_changes)
    results = []
    for item in impacted:
        d = item.as_dict()
        d["modified_in_change"] = item.doc.rel_path in changed_doc_paths
        results.append(d)

    return {
        "schema": "flowform.docsys.impact/1",
        "comparison": diff.reason,
        "base": diff.base,
        "head": diff.head,
        "changed_code_files": sorted(code_changes),
        "changed_doc_files": sorted(doc_changes),
        "impacted_document_count": len(results),
        "impacted_documents": results,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="docsys impact")
    parser.add_argument("--base", help="base commit/ref to diff against")
    parser.add_argument("--head", help="head commit/ref (default HEAD)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    report = impact_report(args.base, args.head)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"Impact report ({report['comparison']})")
    print(f"  code files changed: {len(report['changed_code_files'])}")
    print(f"  docs changed:       {len(report['changed_doc_files'])}")
    print(f"  impacted documents: {report['impacted_document_count']}")
    for d in report["impacted_documents"]:
        flag = "edited" if d["modified_in_change"] else "NOT edited"
        print(f"\n  [{d['confidence'].upper():6}] {d['title']}  ({flag})")
        print(f"           {d['path']}")
        for reason in d["reasons"]:
            print(f"           - {reason}")
        for f in d["matched_files"][:6]:
            print(f"           · {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
