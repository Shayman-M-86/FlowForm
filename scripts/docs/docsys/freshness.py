#!/usr/bin/env python3
"""Documentation freshness detection.

For each document, compare ``verified_against_commit`` against the current
repository and classify how likely the document is out of date. The signal is
the intersection of *what code has changed since the document was verified* and
*which code the document claims to describe* (``related_code``).

Classification (deterministic):

- ``current``          verified against a real commit, and none of the code it
                       owns has changed since
- ``review suggested`` verified, but code it owns changed since verification,
                       OR it is very far behind HEAD in commit distance
- ``likely stale``     verified, and a large share of its owned code changed,
                       or files it names were deleted
- ``unknown``          no ``verified_against_commit`` (scaffold/unchecked), or
                       the recorded commit is missing from history

Scaffolds are ``unknown`` by design: they carry no verified claims yet. Run:

    python3 -m docsys freshness
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import gitutil
from .config import Config
from .model import ROOT, DocSet, Document, pattern_matches

CURRENT = "current"
REVIEW = "review suggested"
STALE = "likely stale"
UNKNOWN = "unknown"

_ORDER = {STALE: 0, REVIEW: 1, UNKNOWN: 2, CURRENT: 3}


@dataclass
class Freshness:
    doc: Document
    classification: str
    reasons: list[str] = field(default_factory=list)
    changed_owned_files: list[str] = field(default_factory=list)
    commit_distance: int | None = None

    def as_dict(self) -> dict:
        return {
            "path": self.doc.rel_path,
            "title": self.doc.title,
            "status": self.doc.status,
            "document_type": self.doc.document_type,
            "verified_against_commit": self.doc.verified_against_commit,
            "classification": self.classification,
            "commit_distance": self.commit_distance,
            "changed_owned_files": sorted(self.changed_owned_files),
            "reasons": self.reasons,
        }


def _owned_changes(doc: Document, changed: list[str]) -> list[str]:
    owned = []
    for f in changed:
        if any(pattern_matches(x, f) for x in doc.exclusion_patterns):
            continue
        patterns = doc.related_patterns + doc.trigger_patterns
        if any(pattern_matches(p, f) for p in patterns):
            owned.append(f)
    return owned


def classify_document(doc: Document, config: Config) -> Freshness:
    commit = doc.verified_against_commit

    # Generated documents are reproducible from the tree, not "verified" in the
    # prose sense; report them as unknown so they never masquerade as current.
    if commit is None:
        reason = (
            "generated document; freshness is defined by regenerating it"
            if doc.is_generated
            else "no verified_against_commit recorded"
        )
        return Freshness(doc, UNKNOWN, [reason])

    if not gitutil.commit_exists(commit):
        return Freshness(
            doc,
            UNKNOWN,
            [f"verified_against_commit {gitutil.short(commit)} is not in history"],
        )

    distance = gitutil.commit_distance(commit)
    diff = gitutil.files_changed_since(commit)
    owned = _owned_changes(doc, diff.files)
    deletions_owned = [f for f in owned if not (ROOT / f).exists()]

    reasons: list[str] = []
    if distance is not None:
        reasons.append(f"{distance} commit(s) since verification")

    # No declared code paths: we cannot reason about owned changes, so fall
    # back to commit distance only.
    has_patterns = bool(doc.related_patterns or doc.trigger_patterns)

    if not has_patterns:
        if distance is not None and distance >= config.stale_commit_distance:
            reasons.append(f"no related_code and {distance} commits behind HEAD")
            return Freshness(doc, REVIEW, reasons, [], distance)
        reasons.append("no related_code to check; only commit distance known")
        return Freshness(doc, CURRENT, reasons, [], distance)

    if not owned:
        reasons.append("no owned code changed since verification")
        if distance is not None and distance >= config.stale_commit_distance:
            reasons.append("but very far behind HEAD; a spot check is prudent")
            return Freshness(doc, REVIEW, reasons, [], distance)
        return Freshness(doc, CURRENT, reasons, [], distance)

    # Some owned code changed. Deletions, or a large share of owned patterns
    # touched, push toward "likely stale".
    owned_pattern_hits = sum(
        1
        for p in (doc.related_patterns + doc.trigger_patterns)
        if any(pattern_matches(p, f) for f in owned)
    )
    total_patterns = max(1, len(doc.related_patterns) + len(doc.trigger_patterns))
    share = owned_pattern_hits / total_patterns

    if deletions_owned:
        reasons.append(
            f"{len(deletions_owned)} owned file(s) were deleted since verification"
        )
        return Freshness(doc, STALE, reasons, owned, distance)
    if share >= 0.5 or len(owned) >= 8:
        reasons.append(
            f"{len(owned)} owned file(s) changed across {owned_pattern_hits}/"
            f"{total_patterns} declared code areas"
        )
        return Freshness(doc, STALE, reasons, owned, distance)

    reasons.append(f"{len(owned)} owned file(s) changed since verification")
    return Freshness(doc, REVIEW, reasons, owned, distance)


def check_all(
    docset: DocSet | None = None, config: Config | None = None
) -> list[Freshness]:
    docset = docset or DocSet.load()
    config = config or Config.load()
    results = [classify_document(d, config) for d in docset.docs]
    results.sort(key=lambda f: (_ORDER[f.classification], f.doc.rel_path))
    return results


def health_report(docset: DocSet | None = None, config: Config | None = None) -> dict:
    results = check_all(docset, config)
    counts: dict[str, int] = {CURRENT: 0, REVIEW: 0, STALE: 0, UNKNOWN: 0}
    for r in results:
        counts[r.classification] += 1
    return {
        "schema": "flowform.docsys.freshness/1",
        "repo_head": gitutil.current_commit(),
        "counts": counts,
        "documents": [r.as_dict() for r in results],
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="docsys freshness")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--only",
        choices=[CURRENT, REVIEW, STALE, UNKNOWN],
        help="show only one classification",
    )
    args = parser.parse_args(argv)

    report = health_report()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    c = report["counts"]
    print(
        f"Freshness @ {gitutil.short(report['repo_head'])}: "
        f"{c[CURRENT]} current, {c[REVIEW]} review, "
        f"{c[STALE]} likely stale, {c[UNKNOWN]} unknown"
    )
    for d in report["documents"]:
        if args.only and d["classification"] != args.only:
            continue
        if d["classification"] == CURRENT and not args.only:
            continue  # keep the default view focused on what needs attention
        print(f"\n  [{d['classification']}] {d['title']}")
        print(f"           {d['path']}")
        for reason in d["reasons"]:
            print(f"           - {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
