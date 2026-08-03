#!/usr/bin/env python3
"""Documentation freshness detection.

For each document, compare ``verified_evidence_digest`` with a digest of the
current committed blobs matched by ``related_code`` and ``change_triggers``.

Classification (deterministic):

- ``current``          recorded and current evidence digests match
- ``likely stale``     the current evidence digest differs
- ``unknown``          no digest is recorded, or evidence cannot be calculated

Scaffolds are ``unknown`` by design: they carry no verified claims yet. Run:

    tools/bin/docsys freshness
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import gitutil
from .config import Config
from .evidence import DIGEST_RE, EvidenceSource
from .model import DocSet, Document

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
    evidence_files: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "path": self.doc.rel_path,
            "title": self.doc.title,
            "status": self.doc.status,
            "document_type": self.doc.document_type,
            "verified_evidence_digest": self.doc.verified_evidence_digest,
            "last_edited": self.doc.last_edited,
            "classification": self.classification,
            "evidence_file_count": len(self.evidence_files),
            "evidence_files": sorted(self.evidence_files),
            "reasons": self.reasons,
        }


def classify_document(
    doc: Document,
    config: Config | None = None,  # retained for caller compatibility
    source: EvidenceSource | None = None,
) -> Freshness:
    del config
    digest = doc.verified_evidence_digest

    if doc.collection == "development-workspace":
        return Freshness(
            doc,
            UNKNOWN,
            ["evidence verification does not apply to Development Workspace"],
        )

    if digest is None:
        reason = (
            "generated document; freshness is defined by regenerating it"
            if doc.is_generated
            else "no verified_evidence_digest recorded"
        )
        return Freshness(doc, UNKNOWN, [reason])

    if not DIGEST_RE.fullmatch(digest):
        return Freshness(
            doc,
            UNKNOWN,
            ["verified_evidence_digest has an invalid format"],
        )

    try:
        source = source or EvidenceSource.from_ref("HEAD")
        snapshot = source.snapshot(doc)
    except RuntimeError as exc:
        return Freshness(doc, UNKNOWN, [f"could not calculate evidence: {exc}"])

    if snapshot.digest == digest:
        return Freshness(
            doc,
            CURRENT,
            [f"{len(snapshot.files)} evidence file(s) match the recorded digest"],
            list(snapshot.files),
        )
    return Freshness(
        doc,
        STALE,
        ["current implementation evidence differs from the recorded digest"],
        list(snapshot.files),
    )


def check_all(
    docset: DocSet | None = None, config: Config | None = None
) -> list[Freshness]:
    docset = docset or DocSet.load()
    config = config or Config.load()
    try:
        source = EvidenceSource.from_ref("HEAD")
    except RuntimeError:
        source = None
    results = [classify_document(d, config, source=source) for d in docset.docs]
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
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--all", action="store_true", dest="show_all")
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--only",
        choices=[CURRENT, REVIEW, STALE, UNKNOWN],
        help="show only one classification",
    )
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    report = health_report()
    selected = [
        item
        for item in report["documents"]
        if (not args.only or item["classification"] == args.only)
        and (args.only or item["classification"] != CURRENT)
    ]
    shown = selected if args.show_all else selected[: args.limit]
    if args.format == "json":
        payload = {
            "schema": report["schema"],
            "counts": report["counts"],
            "total": len(selected),
            "returned": len(shown),
            "truncated": len(shown) < len(selected),
            "items": (
                shown
                if args.details
                else [
                    {
                        "path": item["path"],
                        "title": item["title"],
                        "classification": item["classification"],
                    }
                    for item in shown
                ]
            ),
        }
        print(json.dumps(payload, separators=(",", ":")))
        return 0

    c = report["counts"]
    print(
        f"Freshness @ {gitutil.short(report['repo_head'])}: "
        f"{c[CURRENT]} current, {c[REVIEW]} review, "
        f"{c[STALE]} likely stale, {c[UNKNOWN]} unknown"
    )
    for d in shown:
        print(f"  [{d['classification']}] {d['path']} — {d['title']}")
        if args.details:
            for reason in d["reasons"]:
                print(f"           - {reason}")
    if len(shown) < len(selected):
        print(f"  … {len(selected) - len(shown)} more; use --all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
