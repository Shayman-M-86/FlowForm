#!/usr/bin/env python3
"""Documentation health report and dashboard generator.

Produces two artefacts in the active tree's generated-document directory:

- ``documentation-health.json``  a machine-readable health snapshot
- ``documentation-dashboard.md``  a generated page (front matter conforming to
  the knowledge-network conventions) summarising documentation health for
  humans

The dashboard reports: stale documents, verification-status breakdown, orphan
documents (no inbound or outbound links), heavily connected documents,
unresolved questions, invalid metadata, and broken links. It is generated
output — do not edit it by hand; regenerate with
``tools/bin/docsys health --write``.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from ..config import Config
from ..core import gitutil
from ..core.cli import add_output_args, envelope, markdown_table, paginate
from ..core.model import (
    HEADING_RE,
    ROOT,
    DocSet,
    Document,
    generated_dir_for,
    resolve_docs_root,
)
from .freshness import CURRENT, REVIEW, STALE, UNKNOWN, check_all
from .validate import all_findings

# Documents that are prose-navigation / index pages are expected to have few
# links; only content documents are judged as potential orphans.
_ORPHAN_EXEMPT_TYPES = {"generated"}
_OPEN_QUESTION_HEADING = re.compile(r"open questions?|unresolved|todo", re.I)


def _open_questions(doc: Document) -> list[str]:
    """Return question/TODO entries from explicitly labelled sections."""
    questions: list[str] = []
    capturing = False
    for line in doc.body.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            capturing = bool(_OPEN_QUESTION_HEADING.search(heading.group(2)))
            continue
        if not capturing:
            continue
        value = line.strip()
        if value.startswith("TODO"):
            questions.append(value)
        elif value.startswith(("-", "*")):
            questions.append(value.lstrip("-* ").strip())
    return questions


def connectivity(docset: DocSet) -> dict[str, dict]:
    """Compute inbound/outbound link degree per document."""
    outbound: dict[str, int] = {}
    inbound: dict[str, int] = {d.rel_path: 0 for d in docset.docs}
    for d in docset.docs:
        neigh = docset.neighbours(d)
        outbound[d.rel_path] = len(neigh)
    # Inbound = how many documents list this document as a neighbour.
    for d in docset.docs:
        for n in docset.neighbours(d):
            inbound[n.rel_path] = inbound.get(n.rel_path, 0) + 1
    return {
        d.rel_path: {
            "in": inbound.get(d.rel_path, 0),
            "out": outbound.get(d.rel_path, 0),
        }
        for d in docset.docs
    }


def build_health(docset: DocSet | None = None, config: Config | None = None) -> dict:
    docset = docset or DocSet.load()
    config = config or Config.load()

    freshness = check_all(docset, config)
    fresh_by_class: dict[str, list] = {CURRENT: [], REVIEW: [], STALE: [], UNKNOWN: []}
    for f in freshness:
        fresh_by_class[f.classification].append(f)

    graph = connectivity(docset)
    orphans = [
        d.rel_path
        for d in docset.docs
        if d.document_type not in _ORPHAN_EXEMPT_TYPES
        and graph[d.rel_path]["in"] == 0
        and graph[d.rel_path]["out"] == 0
    ]
    connected = sorted(
        docset.docs,
        key=lambda d: graph[d.rel_path]["in"] + graph[d.rel_path]["out"],
        reverse=True,
    )
    heavily_connected = [
        {
            "title": d.title,
            "path": d.rel_path,
            "in": graph[d.rel_path]["in"],
            "out": graph[d.rel_path]["out"],
        }
        for d in connected[:10]
        if graph[d.rel_path]["in"] + graph[d.rel_path]["out"] > 0
    ]

    open_questions = []
    for d in docset.docs:
        qs = _open_questions(d)
        # A scaffold's TODO placeholders are noise here; count only real docs.
        real = [q for q in qs if not q.startswith("TODO")]
        if real:
            open_questions.append(
                {"title": d.title, "path": d.rel_path, "count": len(real)}
            )

    # Exclude the dashboard's own findings: it is regenerated from the tree, and
    # its report tables would otherwise flag their own escaped example text as
    # problems on the next scan. Real issues in the dashboard are impossible by
    # construction (it is generated), so this cannot hide a genuine defect.
    dashboard_path = (
        generated_dir_for(docset.docs_dir) / "documentation-dashboard.md"
    )
    dash_rel = dashboard_path.resolve().relative_to(ROOT).as_posix()
    findings = [f for f in all_findings(docset) if f.path != dash_rel]
    invalid_metadata = [
        {"path": f.path, "message": f.message} for f in findings if f.kind == "metadata"
    ]
    broken_links = [
        {"path": f.path, "message": f.message} for f in findings if f.kind == "link"
    ]

    status_counts = Counter(d.status for d in docset.docs)
    type_counts = Counter(d.document_type for d in docset.docs)

    return {
        "schema": "flowform.docsys.health/1",
        "docs_root": docset.docs_dir.relative_to(ROOT).as_posix(),
        "repo_head": gitutil.current_commit(),
        "document_count": len(docset.docs),
        "status_counts": dict(status_counts),
        "type_counts": dict(type_counts),
        "freshness_counts": {
            CURRENT: len(fresh_by_class[CURRENT]),
            REVIEW: len(fresh_by_class[REVIEW]),
            STALE: len(fresh_by_class[STALE]),
            UNKNOWN: len(fresh_by_class[UNKNOWN]),
        },
        "stale_documents": [
            f.as_dict() for f in fresh_by_class[STALE] + fresh_by_class[REVIEW]
        ],
        "orphan_documents": orphans,
        "heavily_connected": heavily_connected,
        "open_questions": open_questions,
        "invalid_metadata": invalid_metadata,
        "broken_links": broken_links,
    }


def render_dashboard(health: dict) -> str:
    head = gitutil.short(health["repo_head"])
    fc = health["freshness_counts"]
    sc = health["status_counts"]

    parts = [
        "---",
        "title: Documentation health dashboard",
        "aliases:",
        '  - "Documentation health dashboard"',
        "document_type: generated",
        "status: scaffold",
        "authority: canonical",
        "verified_evidence_digest: null",
        f"last_edited: {date.today().isoformat()}",
        "tags: [meta]",
        "related_code: []",
        "change_triggers:",
        '  - "../../../../tools/flowform_tools/docsys/"',
        "related_docs:",
        '  - "Generated reference documentation"',
        '  - "Documentation model"',
        '  - "Documentation workflow"',
        "---",
        "",
        "# Documentation health dashboard",
        "",
        "Generated snapshot of documentation health. Do not edit by hand; "
        "regenerate with "
        "`tools/bin/docsys health --write`.",
        "",
        "> Generated-document scaffold: this file is reproducible from repository "
        "contents via `tools/flowform_tools/docsys/commands/health.py`.",
        "",
        "## Generator",
        "",
        "`tools/flowform_tools/docsys/commands/health.py` renders this dashboard and its "
        "machine-readable JSON companion.",
        "",
        "## Source files scanned",
        "",
        "The generator scans the active documentation root, its metadata and "
        "links, plus Git metadata used for freshness classification.",
        "",
        "## Regeneration",
        "",
        "Run `tools/bin/docsys health --write` from the "
        "repository root.",
        "",
        "## Manual editing policy",
        "",
        "Do not edit this file manually. Change the generator or its source "
        "documents, then regenerate.",
        "",
        f"Repository head at generation: `{head}`. "
        f"{health['document_count']} documents.",
        "",
        "## Verification status",
        "",
        markdown_table(
            ["Status", "Documents"],
            [[k, v] for k, v in sorted(sc.items())],
        ),
        "## Freshness",
        "",
        markdown_table(
            ["Classification", "Documents"],
            [
                ["Current", fc["current"]],
                ["Review suggested", fc["review suggested"]],
                ["Likely stale", fc["likely stale"]],
                ["Unknown", fc["unknown"]],
            ],
        ),
        "## Documents to review",
        "",
        "Documents whose owned code changed since verification, most urgent first.",
        "",
        markdown_table(
            ["Classification", "Document", "Reason"],
            [
                [
                    d["classification"],
                    d["title"],
                    (d["reasons"][0] if d["reasons"] else ""),
                ]
                for d in health["stale_documents"]
            ],
        ),
        "## Heavily connected documents",
        "",
        markdown_table(
            ["Document", "Inbound", "Outbound"],
            [[d["title"], d["in"], d["out"]] for d in health["heavily_connected"]],
        ),
        "## Orphan documents",
        "",
        "Content documents with no inbound or outbound wiki-link relationships.",
        "",
        (
            markdown_table(["Path"], [[p] for p in health["orphan_documents"]])
            if health["orphan_documents"]
            else "_None._\n"
        ),
        "## Unresolved questions",
        "",
        markdown_table(
            ["Document", "Open questions"],
            [[q["title"], q["count"]] for q in health["open_questions"]],
        ),
        "## Invalid metadata",
        "",
        markdown_table(
            ["Path", "Issue"],
            [[m["path"], m["message"]] for m in health["invalid_metadata"]],
        ),
        "## Broken links",
        "",
        markdown_table(
            ["Path", "Issue"],
            [[m["path"], m["message"]] for m in health["broken_links"]],
        ),
        "## Related documents",
        "",
        "- [[generated-index|Generated reference documentation]]",
        "- [[documentation-model|Documentation model]]",
        "- [[documentation-workflow|Documentation workflow]]",
        "",
    ]
    return "\n".join(parts)


def write_health(
    health: dict | None = None, docs_dir: str | Path | None = None
) -> tuple[Path, Path]:
    if health is None:
        docset = DocSet.load(docs_dir)
        health = build_health(docset)
        resolved_docs_dir = docset.docs_dir
    else:
        resolved_docs_dir = resolve_docs_root(
            docs_dir or health.get("docs_root")
        )
    generated_dir = generated_dir_for(resolved_docs_dir)
    generated_dir.mkdir(parents=True, exist_ok=True)
    health_json_path = generated_dir / "documentation-health.json"
    dashboard_path = generated_dir / "documentation-dashboard.md"
    health_json_path.write_text(json.dumps(health, indent=2) + "\n")
    dashboard_path.write_text(render_dashboard(health))
    return health_json_path, dashboard_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docsys health")
    parser.add_argument("--write", action="store_true", help="write generated health artifacts")
    add_output_args(parser, default_limit=10)
    parser.add_argument(
        "--docs-root",
        default=None,
        help="documentation root (default: active root)",
    )
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    docset = DocSet.load(args.docs_root)
    health = build_health(docset)
    if args.write:
        if args.format == "json":
            parser.error("--write cannot be combined with --format json")
        json_path, dash_path = write_health(health, docset.docs_dir)
        print(f"wrote {json_path.relative_to(ROOT)}")
        print(f"wrote {dash_path.relative_to(ROOT)}")
        return 0

    issues = (
        [
            {"kind": "broken_link", **item}
            for item in health["broken_links"]
        ]
        + [
            {"kind": "invalid_metadata", **item}
            for item in health["invalid_metadata"]
        ]
        + [
            {"kind": "orphan", "path": path}
            for path in health["orphan_documents"]
        ]
    )
    shown, total, _ = paginate(issues, limit=args.limit, show_all=args.show_all)
    fc = health["freshness_counts"]
    if args.format == "json":
        print(
            json.dumps(
                envelope(
                    health["schema"],
                    shown,
                    total=total,
                    freshness_counts=fc,
                ),
                separators=(",", ":"),
            )
        )
        return 0

    print(
        f"Documentation health: {fc['likely stale']} likely stale, "
        f"{fc['review suggested']} review, "
        f"{len(health['broken_links'])} broken links, "
        f"{len(health['invalid_metadata'])} metadata issues"
    )
    if args.details:
        for item in shown:
            print(f"  [{item['kind']}] {item['path']}")
        if len(shown) < total:
            print(f"  … {total - len(shown)} more; use --all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
