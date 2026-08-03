#!/usr/bin/env python3
"""Explainable, advisory documentation debt and split-candidate analysis."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field

from ..core import gitutil
from ..core.cli import add_output_args, envelope, paginate
from ..core.markdown_ast import Node, parse_markdown
from ..core.model import ROOT, DocSet, Document, resolve_docs_root

_WORD = re.compile(r"\b[\w'-]+\b")
_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_WIKI = re.compile(r"\[\[([^\]|]+)")

_DEFAULT_POLICY = {
    "max_words": 1600,
    "max_major_sections": 6,
    "large_section_words": 300,
    "large_section_count": 2,
    "max_code_ratio": 0.4,
    "max_code_roots": 4,
}
_POLICIES = {
    "overview": {**_DEFAULT_POLICY, "max_words": 1400, "max_major_sections": 8},
    "architecture": {**_DEFAULT_POLICY, "max_words": 2800},
    "decision": {**_DEFAULT_POLICY, "max_words": 1600, "max_major_sections": 8},
    "reference": {
        **_DEFAULT_POLICY,
        "max_words": 4500,
        "max_major_sections": 18,
        "large_section_words": 800,
        "large_section_count": 6,
        "max_code_ratio": 0.75,
        "max_code_roots": 10,
    },
    "implementation": {
        **_DEFAULT_POLICY,
        "max_words": 3500,
        "max_code_ratio": 0.7,
    },
    "plan": {**_DEFAULT_POLICY, "max_words": 4500, "max_major_sections": 20},
    "investigation": {
        **_DEFAULT_POLICY,
        "max_words": 5000,
        "max_major_sections": 22,
    },
}


@dataclass
class DocumentMetrics:
    title: str
    path: str
    collection: str
    document_type: str
    word_count: int
    character_count: int
    line_count: int
    paragraph_count: int
    sentence_count: int
    reading_minutes: float
    largest_paragraph_words: int
    heading_count: int
    heading_count_by_level: dict[str, int]
    major_section_count: int
    maximum_heading_depth: int
    largest_section_words: int
    large_section_count: int
    empty_section_count: int
    repeated_headings: list[str]
    skipped_heading_levels: int
    list_count: int
    list_item_count: int
    maximum_list_depth: int
    code_block_count: int
    code_line_count: int
    code_ratio: float
    code_languages: list[str]
    outbound_markdown_links: int
    outbound_wiki_links: int
    related_doc_count: int
    related_code_root_count: int
    topic_cluster_count: int
    commit_count: int | None = None
    contributor_count: int | None = None
    growth_ratio: float | None = None


@dataclass
class DebtFinding:
    code: str
    severity: str
    message: str
    evidence: list[str]
    confidence: float
    suggested_children: list[str] = field(default_factory=list)


def _words(text: str) -> int:
    return len(_WORD.findall(text))


def _sections(nodes: list[Node], major_level: int) -> list[tuple[Node, int]]:
    result = []
    for pos, heading in enumerate(nodes):
        if heading.kind != "heading" or heading.level != major_level:
            continue
        total = 0
        for node in nodes[pos + 1 :]:
            if node.kind == "heading" and node.level <= major_level:
                break
            total += _words(node.text)
        result.append((heading, total))
    return result


def _code_roots(patterns: list[str]) -> set[str]:
    roots = set()
    for pattern in patterns:
        parts = [part for part in pattern.split("/") if part and not any(
            char in part for char in "*?["
        )]
        if parts:
            roots.add("/".join(parts[: min(3, len(parts))]))
    return roots


def _history(doc: Document) -> tuple[int | None, int | None, float | None]:
    _, history, _ = gitutil._run(
        ["log", "--follow", "--format=%H%x09%aN", "--", doc.rel_path]
    )
    rows = [line.split("\t", 1) for line in history.splitlines() if "\t" in line]
    if not rows:
        return None, None, None
    growth = None
    oldest = rows[-1][0]
    code, old_content, _ = gitutil._run(["show", f"{oldest}:{doc.rel_path}"])
    if code == 0:
        old_words = _words(old_content)
        if old_words:
            growth = round((_words(doc.body) - old_words) / old_words, 3)
    return len(rows), len({row[1] for row in rows}), growth


def measure(doc: Document, include_history: bool = False) -> DocumentMetrics:
    ast = parse_markdown(doc.body)
    prose_nodes = [
        node
        for node in ast.nodes
        if node.kind in {"paragraph", "blockquote", "table", "list"}
    ]
    headings = ast.of_kind("heading")
    levels: dict[str, int] = {}
    for heading in headings:
        key = str(heading.level)
        levels[key] = levels.get(key, 0) + 1
    major_level = 2 if any(item.level == 2 for item in headings) else (
        min((item.level for item in headings), default=1)
    )
    sections = _sections(ast.nodes, major_level)
    policy = _POLICIES.get(doc.document_type, _DEFAULT_POLICY)
    section_sizes = [size for _, size in sections]
    paragraphs = ast.of_kind("paragraph")
    code = ast.of_kind("code_block")
    lists = ast.of_kind("list")
    nonblank_lines = max(1, sum(bool(line.strip()) for line in doc.body.splitlines()))
    heading_names = [item.text.casefold() for item in headings]
    repeated = sorted({name for name in heading_names if heading_names.count(name) > 1})
    skipped = sum(
        current.level > previous.level + 1
        for previous, current in zip(headings, headings[1:])
    )
    commit_count = contributor_count = growth_ratio = None
    if include_history:
        commit_count, contributor_count, growth_ratio = _history(doc)
    body_words = _words(doc.body)
    return DocumentMetrics(
        title=doc.title,
        path=doc.rel_path,
        collection=doc.collection,
        document_type=doc.document_type,
        word_count=body_words,
        character_count=len(doc.body),
        line_count=len(doc.body.splitlines()),
        paragraph_count=len(paragraphs),
        sentence_count=len(re.findall(r"[.!?](?:\s|$)", " ".join(n.text for n in prose_nodes))),
        reading_minutes=round(body_words / 220, 1),
        largest_paragraph_words=max((_words(node.text) for node in paragraphs), default=0),
        heading_count=len(headings),
        heading_count_by_level=levels,
        major_section_count=len(sections),
        maximum_heading_depth=max((item.level for item in headings), default=0),
        largest_section_words=max(section_sizes, default=0),
        large_section_count=sum(
            size >= policy["large_section_words"] for size in section_sizes
        ),
        empty_section_count=sum(size == 0 for size in section_sizes),
        repeated_headings=repeated,
        skipped_heading_levels=skipped,
        list_count=len(lists),
        list_item_count=sum(len(item.children) for item in lists),
        maximum_list_depth=max(
            (child.level for item in lists for child in item.children), default=0
        ),
        code_block_count=len(code),
        code_line_count=sum(len(item.text.splitlines()) for item in code),
        code_ratio=round(
            sum(len(item.text.splitlines()) for item in code) / nonblank_lines, 3
        ),
        code_languages=sorted({item.info for item in code if item.info}),
        outbound_markdown_links=len(_LINK.findall(doc.body)),
        outbound_wiki_links=len(_WIKI.findall(doc.body)),
        related_doc_count=len(doc.related_docs),
        related_code_root_count=len(_code_roots(doc.related_patterns)),
        topic_cluster_count=sum(size >= 80 for size in section_sizes),
        commit_count=commit_count,
        contributor_count=contributor_count,
        growth_ratio=growth_ratio,
    )


def _slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.casefold())).strip("-")


def analyse(
    doc: Document, metrics: DocumentMetrics, suggest_splits: bool = False
) -> list[DebtFinding]:
    policy = _POLICIES.get(doc.document_type, _DEFAULT_POLICY)
    conditions = [
        ("word count", metrics.word_count > policy["max_words"]),
        ("major sections", metrics.major_section_count > policy["max_major_sections"]),
        (
            "large sibling sections",
            metrics.large_section_count >= policy["large_section_count"],
        ),
        ("topic clusters", metrics.topic_cluster_count >= 3),
        ("code ratio", metrics.code_ratio > policy["max_code_ratio"]),
        (
            "related code roots",
            metrics.related_code_root_count >= policy["max_code_roots"],
        ),
        ("rapid historical growth", (metrics.growth_ratio or 0) > 1.0),
    ]
    hit = [name for name, matched in conditions if matched]
    if len(hit) < 3:
        return []
    severity = "strong_recommendation" if len(hit) >= 5 else "warning"
    if doc.collection == "development-workspace" and doc.status != "verified":
        severity = "information"
    confidence = round(min(0.95, 0.35 + len(hit) * 0.1), 2)
    evidence = [
        f"{metrics.word_count} words",
        f"{metrics.major_section_count} major sections",
        f"{metrics.large_section_count} large sections",
        f"{metrics.topic_cluster_count} substantial topic clusters",
        f"{metrics.related_code_root_count} related-code roots",
    ]
    suggestions = []
    if suggest_splits:
        ast = parse_markdown(doc.body)
        major = [node for node in ast.of_kind("heading") if node.level == 2]
        base = doc.path.parent if doc.is_folder_head else doc.path.with_suffix("")
        suggestions = (
            [str((base / f"{base.name}-index.md").relative_to(ROOT))]
            if not doc.is_folder_head
            else []
        ) + [
            str((base / f"{_slug(node.text)}.md").relative_to(ROOT))
            for node in major
            if _slug(node.text)
        ]
    return [
        DebtFinding(
            "split_candidate",
            severity,
            "This document may contain several independently maintainable topics.",
            evidence + [f"signals: {', '.join(hit)}"],
            confidence,
            suggestions,
        )
    ]


def build_report(
    docset: DocSet,
    collection: str | None = "project-knowledge",
    paths: set[str] | None = None,
    include_history: bool = False,
    suggest_splits: bool = False,
) -> dict:
    documents = []
    for doc in docset.docs:
        if collection and doc.collection != collection:
            continue
        if paths is not None and doc.rel_path not in paths:
            continue
        metrics = measure(doc, include_history)
        documents.append(
            {
                "metrics": asdict(metrics),
                "findings": [
                    asdict(item) for item in analyse(doc, metrics, suggest_splits)
                ],
            }
        )
    return {
        "schema": "flowform.docsys.debt/1",
        "docs_root": docset.docs_dir.relative_to(ROOT).as_posix(),
        "document_count": len(documents),
        "documents": documents,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docsys debt")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--docs-root", default="docs")
    parser.add_argument(
        "--collection",
        choices=["project-knowledge", "development-workspace", "legacy", "root"],
        default="project-knowledge",
        help="collection to analyse (default: project-knowledge)",
    )
    parser.add_argument("--changed", action="store_true")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--suggest-splits", action="store_true")
    add_output_args(parser, default_limit=10)
    args = parser.parse_args(argv)
    try:
        shown, _, _ = paginate([], limit=args.limit, show_all=args.show_all)
    except ValueError as exc:
        parser.error(str(exc))
        parser.error("--limit must be at least 1")
    docset = DocSet.load(resolve_docs_root(args.docs_root))
    selected = set(args.paths)
    if args.changed:
        selected.update(
            path
            for path in gitutil.changed_files().files
            if path.startswith(docset.docs_dir.relative_to(ROOT).as_posix() + "/")
        )
    selected_paths = selected if args.paths or args.changed else None
    report = build_report(
        docset,
        args.collection,
        selected_paths,
        args.history,
        args.suggest_splits,
    )
    selected_results = [
        result for result in report["documents"] if result["findings"]
    ]
    shown, total, _ = paginate(
        selected_results, limit=args.limit, show_all=args.show_all
    )
    if args.format == "json":
        payload = envelope(
            report["schema"],
            shown,
            total=total,
            document_count=report["document_count"],
        )
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(f"Documentation debt: {report['document_count']} document(s)")
        for result in shown:
            metrics = result["metrics"]
            findings = result["findings"]
            print(f"{metrics['path']} ({metrics['word_count']} words)")
            for finding in findings:
                print(
                  f"  {finding['severity']}: {finding['message']} "
                  f"(confidence {finding['confidence']:.0%})"
                )
                if args.details:
                    for evidence in finding["evidence"]:
                        print(f"    - {evidence}")
                    for child in finding["suggested_children"]:
                        print(f"    -> {child}")
        if len(shown) < total:
            print(f"… {total - len(shown)} more; use --all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
