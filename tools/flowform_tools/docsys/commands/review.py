#!/usr/bin/env python3
"""Correlate staged documentation drift signals without blocking commits."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field

from ..config import Config
from ..core import gitutil
from ..core.model import ROOT, DocSet, Document
from .debt import DebtFinding, analyse, measure
from .evidence import EvidenceSource, load_index_document
from .freshness import STALE, Freshness, classify_document
from .health import connectivity
from .impact import ImpactedDoc, detect_impact
from .validate import Finding, all_findings

_DOCUMENTATION_SUFFIXES = (".md", ".mdx", ".rst", ".adoc")
_IMPACT_WEIGHT = {"high": 1.0, "medium": 0.8}


def _is_implementation_path(path: str) -> bool:
    lowered = path.casefold()
    return not (
        lowered.startswith(("docs/", "old-docs/"))
        or lowered.endswith(_DOCUMENTATION_SUFFIXES)
    )


def _implementation_scope(path: str) -> str:
    """Return a stable ownership-sized scope for one implementation path."""
    parts = path.split("/")
    root = parts[0]
    if root == "backend":
        if len(parts) >= 3 and parts[1] == "app":
            return "/".join(parts[:3])
        return "/".join(parts[:2]) if len(parts) >= 2 else root
    if root == "frontend":
        if len(parts) >= 3 and parts[1] in {"apps", "packages"}:
            return "/".join(parts[:3])
        return "/".join(parts[:2]) if len(parts) >= 2 else root
    if root == "infra":
        if len(parts) >= 3 and parts[1] == "deployment":
            return "/".join(parts[:3])
        return "/".join(parts[:2]) if len(parts) >= 2 else root
    if root == "tools":
        if len(parts) >= 3 and parts[1] == "flowform_tools":
            return "/".join(parts[:3])
        return "/".join(parts[:2]) if len(parts) >= 2 else root
    if len(parts) >= 2 and root in {"scripts", ".github", ".githooks"}:
        return "/".join(parts[:2])
    return root


def _knowledge_area(path: str) -> str:
    parts = path.split("/")
    return parts[2] if len(parts) > 2 else "project-knowledge"


@dataclass
class ReviewCandidate:
    path: str
    title: str
    confidence: str
    status: str
    freshness: str
    matched_files: list[str]
    implementation_scopes: list[str]
    exact_evidence_files: list[str]
    debt_findings: list[dict]
    validation_findings: list[dict]
    graph_in: int
    graph_out: int
    priority: float


@dataclass
class StagedReview:
    comparison: str
    reasons: list[str] = field(default_factory=list)
    candidates: list[ReviewCandidate] = field(default_factory=list)

    @property
    def recommended(self) -> bool:
        return bool(self.reasons)

    def as_dict(self) -> dict:
        return {
            "schema": "flowform.docsys.review/1",
            "comparison": self.comparison,
            "recommended": self.recommended,
            "reasons": self.reasons,
            "candidates": [asdict(candidate) for candidate in self.candidates],
        }


def _candidate(
    impact: ImpactedDoc,
    source: EvidenceSource,
    graph: dict[str, dict],
    validation_by_path: dict[str, list[Finding]],
    config: Config,
) -> tuple[ReviewCandidate, Freshness, list[DebtFinding]]:
    doc = impact.doc
    freshness = classify_document(doc, source=source)
    debt = analyse(doc, measure(doc))
    validation = validation_by_path.get(doc.rel_path, [])
    matched_files = sorted(
        {match.file for match in impact.matches if _is_implementation_path(match.file)}
    )
    scopes = sorted({_implementation_scope(path) for path in matched_files})
    exact_files = sorted(
        {
            match.file
            for match in impact.matches
            if match.source == "related_code"
            and match.kind == "exact"
            and _is_implementation_path(match.file)
        }
    )
    links = graph.get(doc.rel_path, {"in": 0, "out": 0})
    impact_weight = _IMPACT_WEIGHT.get(impact.confidence, config.trigger_weight)
    priority = impact_weight
    if freshness.classification == STALE:
        priority += 0.5
    if debt:
        priority += 0.25
    if validation:
        priority += 0.2
    priority += min(links["in"] + links["out"], 10) * 0.02
    return (
        ReviewCandidate(
            path=doc.rel_path,
            title=doc.title,
            confidence=impact.confidence,
            status=doc.status,
            freshness=freshness.classification,
            matched_files=matched_files,
            implementation_scopes=scopes,
            exact_evidence_files=exact_files,
            debt_findings=[asdict(item) for item in debt],
            validation_findings=[asdict(item) for item in validation],
            graph_in=links["in"],
            graph_out=links["out"],
            priority=round(priority, 2),
        ),
        freshness,
        debt,
    )


def build_staged_review(
    *,
    staged_paths: list[str] | None = None,
    docset: DocSet | None = None,
    source: EvidenceSource | None = None,
    config: Config | None = None,
) -> StagedReview:
    """Compose impact, evidence, validation, debt, and graph signals."""
    config = config or Config.load()
    docset = docset or DocSet.load()
    explicit_paths = staged_paths is not None
    if staged_paths is None:
        diff = gitutil.staged_files()
        staged_paths = diff.files
        comparison = diff.reason
    else:
        comparison = "explicit staged paths"
    source = source or EvidenceSource.from_index()
    if not explicit_paths:
        docset = DocSet(
            [
                load_index_document(doc)
                for doc in docset.docs
                if doc.rel_path in source.entries
            ],
            docset.docs_dir,
            [
                path
                for path in docset.unparsed_paths
                if path.relative_to(ROOT).as_posix() in source.entries
            ],
        )

    docs_prefix = docset.docs_dir.relative_to(ROOT).as_posix() + "/"
    staged_docs = {
        path
        for path in staged_paths
        if path.startswith(docs_prefix) and path.endswith(".md")
    }
    implementation_paths = [
        path for path in staged_paths if _is_implementation_path(path)
    ]
    impacts = [
        impact
        for impact in detect_impact(implementation_paths, docset)
        if impact.doc.collection == "project-knowledge"
        and not impact.doc.is_generated
        and impact.doc.rel_path not in staged_docs
    ]
    if not impacts:
        return StagedReview(comparison)

    validation_by_path: dict[str, list[Finding]] = {}
    for finding in all_findings(docset, "editing"):
        validation_by_path.setdefault(finding.path, []).append(finding)
    graph = connectivity(docset)

    candidates: list[ReviewCandidate] = []
    freshness_by_path: dict[str, Freshness] = {}
    debt_by_path: dict[str, list[DebtFinding]] = {}
    for impact in impacts:
        candidate, freshness, debt = _candidate(
            impact,
            source,
            graph,
            validation_by_path,
            config,
        )
        candidates.append(candidate)
        freshness_by_path[candidate.path] = freshness
        debt_by_path[candidate.path] = debt

    reasons: list[str] = []
    direct_candidates = [
        candidate for candidate in candidates if candidate.exact_evidence_files
    ]
    direct_files = {
        path
        for candidate in direct_candidates
        for path in candidate.exact_evidence_files
    }
    if len(direct_candidates) >= 2 and len(direct_files) >= 2:
        reasons.append(
            "multiple Project Knowledge documents have independent "
            "direct-evidence changes"
        )

    all_scopes = {
        scope for candidate in candidates for scope in candidate.implementation_scopes
    }
    knowledge_areas = {_knowledge_area(candidate.path) for candidate in candidates}
    if len(all_scopes) >= 2 and len(knowledge_areas) >= 2:
        reasons.append(
            "implementation changes cross ownership scopes and documentation areas"
        )

    for candidate in candidates:
        if (
            candidate.confidence in {"high", "medium"}
            and len(candidate.implementation_scopes) >= 2
        ):
            reasons.append(
                f"{candidate.title} is affected across multiple implementation scopes"
            )
        if freshness_by_path[candidate.path].classification == STALE:
            reasons.append(
                f"{candidate.title} no longer matches its staged evidence snapshot"
            )
        if candidate.confidence in {"high", "medium"} and debt_by_path[candidate.path]:
            severity = debt_by_path[candidate.path][0].severity.replace("_", " ")
            reasons.append(
                f"{candidate.title} has {severity} complexity debt and direct impact"
            )

    reasons = list(dict.fromkeys(reasons))
    candidates.sort(key=lambda candidate: (-candidate.priority, candidate.path))
    return StagedReview(comparison, reasons, candidates)


def _render(review: StagedReview) -> None:
    if not review.recommended:
        return
    print()
    print("DOCUMENTATION REVIEW RECOMMENDED — COMMIT WILL CONTINUE")
    print("Docsys found correlated drift signals in the staged change:")
    for reason in review.reasons[:6]:
        print(f"  - {reason}")
    for candidate in review.candidates[:6]:
        signals = [candidate.confidence, candidate.status, candidate.freshness]
        if candidate.debt_findings:
            signals.append(candidate.debt_findings[0]["severity"].replace("_", " "))
        if candidate.validation_findings:
            signals.append(f"{len(candidate.validation_findings)} validation finding(s)")
        links = candidate.graph_in + candidate.graph_out
        if links:
            signals.append(f"{links} graph links")
        print(f"  [{', '.join(signals)}] {candidate.path}")
    if len(review.candidates) > 6:
        print(f"  ... {len(review.candidates) - 6} more mapped documents")
    print()
    print("Inspect the evidence before deciding whether prose changed:")
    print("  tools/bin/docsys review --staged --format json")
    print("  tools/bin/docsys impact --staged --all --details")
    print(
        "No documentation edit is required when the documented behaviour is unchanged."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docsys review")
    parser.add_argument("--staged", action="store_true", required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    review = build_staged_review()
    if args.format == "json":
        print(json.dumps(review.as_dict(), separators=(",", ":")))
    else:
        _render(review)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
