#!/usr/bin/env python3
"""Task context generation.

Given a natural-language task and/or a set of changed files, assemble the
*smallest useful* documentation context for it, rather than loading the whole
tree. This is the retrieval primitive AI agents call before working: it returns
a focused bundle so an agent reads a handful of relevant documents instead of
searching large portions of the repository.

The bundle contains:

- ``primary_documents``     the strongest matches (query ranking and/or the
                            documents that own the changed files)
- ``neighbouring_documents`` one hop out in the wiki-link graph, for context
- ``implementation_locations`` the ``related_code`` paths those documents point
                            at — where the actual behaviour lives
- ``workflows``             relevant ``30-workflows`` documents among matches
- ``open_questions``        unresolved-question sections harvested from primary
                            documents, so the agent inherits known unknowns

    python3 -m docsys context --task "add a new survey question type"
    python3 -m docsys context --changed backend/app/routes/surveys.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from . import gitutil
from .impact import detect_impact
from .model import DocSet, Document
from .query import QueryEngine

_OPEN_Q_HEADINGS = re.compile(r"open questions?|unresolved|todo", re.I)


@dataclass
class ContextBundle:
    task: str
    changed_files: list[str]
    primary: list[Document] = field(default_factory=list)
    neighbours: list[Document] = field(default_factory=list)
    implementation_locations: list[str] = field(default_factory=list)
    workflows: list[Document] = field(default_factory=list)
    open_questions: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        def brief(d: Document) -> dict:
            return {
                "path": d.rel_path,
                "title": d.title,
                "document_type": d.document_type,
                "status": d.status,
                "summary": _first_sentence(d),
            }

        return {
            "schema": "flowform.docsys.context/1",
            "task": self.task,
            "changed_files": self.changed_files,
            "primary_documents": [brief(d) for d in self.primary],
            "neighbouring_documents": [brief(d) for d in self.neighbours],
            "implementation_locations": self.implementation_locations,
            "workflows": [brief(d) for d in self.workflows],
            "open_questions": self.open_questions,
        }


def _first_sentence(doc: Document) -> str:
    for line in doc.body.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith(">"):
            return " ".join(s.split())[:200]
    return ""


def _open_questions(doc: Document) -> list[str]:
    """Harvest bullet/prose lines under an open-questions-style heading."""
    lines = doc.body.splitlines()
    out: list[str] = []
    capturing = False
    for line in lines:
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            capturing = bool(_OPEN_Q_HEADINGS.search(h.group(2)))
            continue
        if capturing:
            s = line.strip()
            if not s:
                continue
            if s.startswith("TODO"):
                # A scaffold placeholder is itself an open question.
                out.append(s)
            elif s.startswith(("-", "*")):
                out.append(s.lstrip("-* ").strip())
    return out


def build_context(
    task: str = "",
    changed_files: list[str] | None = None,
    docset: DocSet | None = None,
    max_primary: int = 5,
    max_neighbours: int = 6,
) -> ContextBundle:
    docset = docset or DocSet.load()
    changed_files = changed_files or []

    primary: list[Document] = []
    primary_paths: set[str] = set()

    def add_primary(doc: Document):
        if doc.rel_path not in primary_paths:
            primary.append(doc)
            primary_paths.add(doc.rel_path)

    # 1. Documents that own the changed files (highest-confidence first).
    if changed_files:
        code_changes = [f for f in changed_files if not f.startswith("docs/")]
        for item in detect_impact(code_changes, docset):
            add_primary(item.doc)

    # 2. Query matches for the task text.
    if task:
        engine = QueryEngine(docset)
        for scored in engine.search(task, limit=max_primary * 2):
            add_primary(scored.doc)

    # Prefer documents carrying real claims; keep the bundle small.
    primary.sort(
        key=lambda d: {"verified": 0, "draft": 1, "scaffold": 2}.get(d.status, 3)
    )
    primary = primary[:max_primary]
    primary_paths = {d.rel_path for d in primary}

    # 3. One hop out in the link graph.
    neighbours: list[Document] = []
    neighbour_paths: set[str] = set()
    for d in primary:
        for n in docset.neighbours(d):
            if n.rel_path not in primary_paths and n.rel_path not in neighbour_paths:
                neighbours.append(n)
                neighbour_paths.add(n.rel_path)
    neighbours = neighbours[:max_neighbours]

    # 4. Implementation locations from primary docs' declared code.
    impl: list[str] = []
    seen_impl: set[str] = set()
    for d in primary:
        for pattern in d.related_patterns:
            if pattern not in seen_impl:
                impl.append(pattern)
                seen_impl.add(pattern)

    # 5. Relevant workflows among primary + neighbours.
    workflows = [d for d in primary + neighbours if d.document_type == "workflow"]

    # 6. Open questions harvested from primary documents.
    open_qs: list[dict] = []
    for d in primary:
        qs = _open_questions(d)
        if qs:
            open_qs.append({"document": d.title, "questions": qs[:5]})

    return ContextBundle(
        task=task,
        changed_files=changed_files,
        primary=primary,
        neighbours=neighbours,
        implementation_locations=impl,
        workflows=workflows,
        open_questions=open_qs,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="docsys context")
    parser.add_argument("--task", default="", help="natural-language task")
    parser.add_argument(
        "--changed",
        nargs="*",
        default=None,
        help="changed file paths (default: working-tree diff if no task given)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    changed = args.changed
    if changed is None and not args.task:
        changed = gitutil.changed_files().files

    bundle = build_context(task=args.task, changed_files=changed or [])
    if args.json:
        print(json.dumps(bundle.as_dict(), indent=2))
        return 0

    print(f"Context for: {args.task or '(changed files)'}")
    print("\nPrimary documents:")
    for d in bundle.primary:
        print(f"  - {d.title} [{d.status}]  {d.rel_path}")
    print("\nNeighbouring documents:")
    for d in bundle.neighbours:
        print(f"  - {d.title}  {d.rel_path}")
    print("\nImplementation locations:")
    for loc in bundle.implementation_locations:
        print(f"  - {loc}")
    if bundle.workflows:
        print("\nRelevant workflows:")
        for d in bundle.workflows:
            print(f"  - {d.title}  {d.rel_path}")
    if bundle.open_questions:
        print("\nOpen questions:")
        for oq in bundle.open_questions:
            print(f"  {oq['document']}:")
            for q in oq["questions"]:
                print(f"    · {q}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
