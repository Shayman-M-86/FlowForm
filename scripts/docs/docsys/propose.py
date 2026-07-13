#!/usr/bin/env python3
"""Agent-assisted documentation update proposals.

This tool never rewrites documentation. It runs the deterministic half of the
update workflow and hands an agent a *review brief* per affected document:

1. detect affected documentation (via :mod:`docsys.impact`)
2. gather only the relevant context (via :mod:`docsys.context`)
3. surface the concrete code changes the agent must judge
4. state the decision the agent must make and the constraints on any edit

The agent then decides whether documented behaviour actually changed, and — if
so — proposes edits that a human reviews. Every proposed change must be
explained and reviewable; nothing here writes to ``docs/``.

The output is a JSON "proposal packet". Agents (or the MCP server) consume it;
the ``--markdown`` view is for humans. Run:

    python3 -m docsys propose --base origin/main
"""

from __future__ import annotations

import json

from .context import build_context
from .impact import impact_report
from .model import DocSet, Document

# The instruction block is deliberately explicit: it is the contract the agent
# operates under, and it forbids silent rewrites.
AGENT_CONTRACT = [
    "Code is the source of truth; documentation is a projection of understanding.",
    "First decide whether the documented behaviour actually changed. If it did "
    "not, propose no edit and say why.",
    "If it did change, propose the smallest edit that restores accuracy, keep "
    "the document at its layer's altitude, and explain every change.",
    "Update verified_against_commit only when you have checked the claim "
    "against the current implementation.",
    "Never invent facts to fill scaffold sections; mark missing evidence instead.",
    "Do not apply edits directly. Emit proposed edits for human review.",
]


def _doc_brief(doc: Document, matched_files: list[str], confidence: str) -> dict:
    context = build_context(
        task=doc.title,
        changed_files=matched_files,
        max_primary=4,
        max_neighbours=4,
    )
    return {
        "document": {
            "title": doc.title,
            "path": doc.rel_path,
            "document_type": doc.document_type,
            "status": doc.status,
            "authority": doc.authority,
            "verified_against_commit": doc.verified_against_commit,
        },
        "impact_confidence": confidence,
        "changed_code_files": sorted(matched_files),
        "declared_code": list(doc.related_patterns),
        "decision_required": (
            "Did any of the changed code files alter behaviour that this "
            "document describes? If yes, propose reviewable edits; if no, "
            "record that the document remains accurate."
        ),
        "context": {
            "neighbouring_documents": [
                n["title"] for n in context.as_dict()["neighbouring_documents"]
            ],
            "implementation_locations": context.implementation_locations,
            "open_questions": context.open_questions,
        },
        "headings": list(doc.headings),
    }


def build_proposal_packet(
    base: str | None = None,
    head: str | None = None,
    min_confidence: str = "low",
    docset: DocSet | None = None,
) -> dict:
    docset = docset or DocSet.load()
    report = impact_report(base, head, docset)

    order = {"high": 0, "medium": 1, "low": 2}
    threshold = order.get(min_confidence, 2)

    briefs = []
    for item in report["impacted_documents"]:
        if order[item["confidence"]] > threshold:
            continue
        if item["modified_in_change"]:
            # Already edited in this change; note it but do not ask for a rewrite.
            continue
        doc = docset.by_rel(item["path"])
        if doc is None:
            continue
        briefs.append(_doc_brief(doc, item["matched_files"], item["confidence"]))

    return {
        "schema": "flowform.docsys.proposal/1",
        "comparison": report["comparison"],
        "base": report["base"],
        "head": report["head"],
        "agent_contract": AGENT_CONTRACT,
        "changed_code_files": report["changed_code_files"],
        "already_modified_docs": [
            d["path"] for d in report["impacted_documents"] if d["modified_in_change"]
        ],
        "proposal_count": len(briefs),
        "proposals": briefs,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="docsys propose")
    parser.add_argument("--base", help="base commit/ref to diff against")
    parser.add_argument("--head", help="head commit/ref (default HEAD)")
    parser.add_argument(
        "--min-confidence",
        choices=["high", "medium", "low"],
        default="medium",
        help="lowest impact confidence to raise a proposal for",
    )
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args(argv)

    packet = build_proposal_packet(
        args.base, args.head, min_confidence=args.min_confidence
    )
    if not args.markdown:
        print(json.dumps(packet, indent=2))
        return 0

    print("# Documentation update proposals\n")
    print(f"Comparison: `{packet['comparison']}`\n")
    print("## Agent contract\n")
    for rule in packet["agent_contract"]:
        print(f"- {rule}")
    print(f"\n## Proposals ({packet['proposal_count']})\n")
    for p in packet["proposals"]:
        d = p["document"]
        print(f"### {d['title']}  ({p['impact_confidence']} confidence)\n")
        print(f"- Path: `{d['path']}`  ·  status: {d['status']}")
        print(f"- Changed code: {', '.join(p['changed_code_files'][:8])}")
        print(f"- Decision: {p['decision_required']}\n")
    if packet["already_modified_docs"]:
        print("## Already edited in this change\n")
        for path in packet["already_modified_docs"]:
            print(f"- `{path}`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
