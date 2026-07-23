#!/usr/bin/env python3
"""Documentation health report and dashboard generator.

Produces two artefacts in ``docs/90-generated/``:

- ``documentation-health.json``  a machine-readable health snapshot
- ``documentation-dashboard.md``  a generated page (front matter conforming to
  the knowledge-network conventions) summarising documentation health for
  humans

The dashboard reports: stale documents, verification-status breakdown, orphan
documents (no inbound or outbound links), heavily connected documents,
unresolved questions, invalid metadata, and broken links. It is generated
output — do not edit it by hand; regenerate with ``python3 -m docsys health``.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from . import gitutil
from .config import Config
from .context import _open_questions
from .freshness import CURRENT, REVIEW, STALE, UNKNOWN, check_all
from .model import GENERATED_DIR, ROOT, DocSet
from .validate import all_findings

DASHBOARD_PATH = GENERATED_DIR / "documentation-dashboard.md"
HEALTH_JSON_PATH = GENERATED_DIR / "documentation-health.json"

# Documents that are prose-navigation / index pages are expected to have few
# links; only content documents are judged as potential orphans.
_ORPHAN_EXEMPT_TYPES = {"generated"}


def _connectivity(docset: DocSet) -> dict[str, dict]:
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

    connectivity = _connectivity(docset)
    orphans = [
        d.rel_path
        for d in docset.docs
        if d.document_type not in _ORPHAN_EXEMPT_TYPES
        and connectivity[d.rel_path]["in"] == 0
        and connectivity[d.rel_path]["out"] == 0
    ]
    connected = sorted(
        docset.docs,
        key=lambda d: connectivity[d.rel_path]["in"] + connectivity[d.rel_path]["out"],
        reverse=True,
    )
    heavily_connected = [
        {
            "title": d.title,
            "path": d.rel_path,
            "in": connectivity[d.rel_path]["in"],
            "out": connectivity[d.rel_path]["out"],
        }
        for d in connected[:10]
        if connectivity[d.rel_path]["in"] + connectivity[d.rel_path]["out"] > 0
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
    dash_rel = DASHBOARD_PATH.resolve().relative_to(ROOT).as_posix()
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


def _cell(value) -> str:
    """Escape a value for a Markdown table cell.

    Finding messages can contain ``[[wiki link]]`` and ``|`` characters. Left
    raw, those would corrupt the table and be re-parsed as real wiki links by
    the link validator, making the generated dashboard fail validation because
    it *reports* a broken link. Escape brackets and pipes so cell text is inert.
    """
    text = str(value)
    text = text.replace("|", "\\|")
    text = text.replace("[[", "&#91;&#91;").replace("]]", "&#93;&#93;")
    return text


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_None._\n"
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for r in rows:
        out.append("| " + " | ".join(_cell(c) for c in r) + " |")
    return "\n".join(out) + "\n"


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
        "verified_against_commit: null",
        "tags: [meta]",
        "related_code:",
        '  - "../../scripts/docs/docsys/"',
        "related_docs:",
        '  - "Generated documentation"',
        '  - "Documentation model"',
        '  - "Documentation generator guide"',
        "---",
        "",
        "# Documentation health dashboard",
        "",
        "Generated snapshot of documentation health. Do not edit by hand; "
        "regenerate with `python3 -m docsys health`.",
        "",
        "> Generated-document scaffold: this file is reproducible from repository "
        "contents via `scripts/docs/docsys/health.py`.",
        "",
        f"Repository head at generation: `{head}`. "
        f"{health['document_count']} documents.",
        "",
        "## Verification status",
        "",
        _md_table(
            ["Status", "Documents"],
            [[k, v] for k, v in sorted(sc.items())],
        ),
        "## Freshness",
        "",
        _md_table(
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
        _md_table(
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
        _md_table(
            ["Document", "Inbound", "Outbound"],
            [[d["title"], d["in"], d["out"]] for d in health["heavily_connected"]],
        ),
        "## Orphan documents",
        "",
        "Content documents with no inbound or outbound wiki-link relationships.",
        "",
        (
            _md_table(["Path"], [[p] for p in health["orphan_documents"]])
            if health["orphan_documents"]
            else "_None._\n"
        ),
        "## Unresolved questions",
        "",
        _md_table(
            ["Document", "Open questions"],
            [[q["title"], q["count"]] for q in health["open_questions"]],
        ),
        "## Invalid metadata",
        "",
        _md_table(
            ["Path", "Issue"],
            [[m["path"], m["message"]] for m in health["invalid_metadata"]],
        ),
        "## Broken links",
        "",
        _md_table(
            ["Path", "Issue"],
            [[m["path"], m["message"]] for m in health["broken_links"]],
        ),
        "## Related documents",
        "",
        "- [[90-generated/README|Generated documentation]]",
        "- [[documentation-model|Documentation model]]",
        "- [[documentation-generator-guide|Documentation generator guide]]",
        "",
    ]
    return "\n".join(parts)


def write_health(health: dict | None = None) -> tuple[Path, Path]:
    health = health or build_health()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    HEALTH_JSON_PATH.write_text(json.dumps(health, indent=2) + "\n")
    DASHBOARD_PATH.write_text(render_dashboard(health))
    return HEALTH_JSON_PATH, DASHBOARD_PATH


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="docsys health")
    parser.add_argument("--json", action="store_true", help="print JSON, do not write")
    args = parser.parse_args(argv)

    health = build_health()
    if args.json:
        print(json.dumps(health, indent=2))
        return 0
    json_path, dash_path = write_health(health)
    print(f"wrote {json_path.relative_to(ROOT)}")
    print(f"wrote {dash_path.relative_to(ROOT)}")
    fc = health["freshness_counts"]
    print(
        f"  {fc['likely stale']} likely stale, {fc['review suggested']} review, "
        f"{len(health['broken_links'])} broken links, "
        f"{len(health['invalid_metadata'])} metadata issues"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
