#!/usr/bin/env python3
"""Narrow, deterministic documentation discovery for ``docsys find``."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

from ..contracts import FindRequest, execute_find
from ..core.model import DocSet, Document


@dataclass(frozen=True)
class ScoredDoc:
    """Compatibility projection for internal callers being retired."""

    doc: Document
    score: float
    matched_terms: set[str]
    reasons: list[str]
    snippet: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.doc.rel_path,
            "title": self.doc.title,
            "document_type": self.doc.document_type,
            "authority": self.doc.authority,
            "collection": self.doc.collection,
            "status": self.doc.status,
            "tags": sorted(self.doc.tags),
            "score": self.score,
            "matched_terms": sorted(self.matched_terms),
            "reasons": self.reasons,
            "snippet": self.snippet,
        }


class QueryEngine:
    """Legacy in-process adapter over the canonical find contract.

    The public agent-facing command is ``docsys find``. This adapter remains
    only so non-exposed internal modules can be changed independently.
    """

    def __init__(self, docset: DocSet):
        self.docset = docset

    def search(
        self,
        query: str,
        limit: int = 10,
        doc_type: str | None = None,
        tag: str | None = None,
        min_status: str | None = None,
        collection: str | None = None,
        authority: str | None = None,
        status: str | None = None,
    ) -> list[ScoredDoc]:
        status_rank = {"scaffold": 0, "draft": 1, "verified": 2}
        docs = [
            doc
            for doc in self.docset.docs
            if (authority is None or doc.authority == authority)
            and (
                min_status is None
                or status_rank.get(doc.status, 0) >= status_rank.get(min_status, 0)
            )
        ]
        filtered = DocSet(docs, self.docset.docs_dir, self.docset.unparsed_paths)
        response = execute_find(
            FindRequest(
                query=query,
                match="any",
                limit=min(limit, 20),
                collections=(collection,) if collection else (),
                types=(doc_type,) if doc_type else (),
                statuses=(status,) if status else (),
                tags=(tag,) if tag else (),
                explain=True,
                unbounded=limit > 20,
            ),
            filtered,
        )
        by_path = {doc.rel_path: doc for doc in docs}
        return [
            ScoredDoc(
                doc=by_path[item.path],
                score=item.score or 0.0,
                matched_terms=set(item.matched_terms),
                reasons=list(item.reasons),
                snippet=item.snippet or "",
            )
            for item in response.items[:limit]
        ]


def search(query: str, limit: int = 10, **kwargs: Any) -> list[ScoredDoc]:
    return QueryEngine(DocSet.load()).search(query, limit=limit, **kwargs)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docsys find",
        description="Find a small, relevant set of documentation.",
    )
    parser.add_argument("terms", nargs="*", help="discriminating search terms")
    parser.add_argument(
        "--match",
        choices=["all", "any", "phrase"],
        default="all",
        help="term matching mode (default: all)",
    )
    parser.add_argument("--scope", help="documentation path prefix")
    parser.add_argument(
        "--code",
        action="append",
        default=[],
        help="exact related_code repository file (repeatable)",
    )
    parser.add_argument("--collection", action="append", default=[])
    parser.add_argument("--type", dest="types", action="append", default=[])
    parser.add_argument(
        "--status",
        action="append",
        choices=["scaffold", "draft", "verified"],
        default=[],
    )
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument(
        "--in",
        dest="fields",
        action="append",
        choices=["title", "path", "heading", "tag", "related-code", "body"],
        default=[],
        help="search only selected fields (repeatable)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        metavar="N",
        help="maximum results, 1-20 (default: 3)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="unbounded",
        help="return every match",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="include scores, match reasons, and snippets",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format (default: text)",
    )
    return parser


def _print_text(response) -> None:
    if not response.items:
        print("no matching documents")
        return
    for item in response.items:
        print(f"[{item.status}] {item.path} — {item.title} — {item.summary}")
        if response.explain:
            print(f"  score: {item.score}")
            if item.matched_terms:
                print(f"  terms: {', '.join(item.matched_terms)}")
            if item.reasons:
                print(f"  reasons: {', '.join(item.reasons)}")
            if item.snippet:
                print(f"  snippet: {item.snippet}")
    if response.warning:
        print(f"warning: {response.warning}")
    if response.truncated:
        print(
            f"showing {response.returned} of {response.total}; "
            "use --all for all matches"
        )


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        request = FindRequest(
            query=" ".join(args.terms),
            scope=args.scope,
            code_paths=tuple(args.code),
            match=args.match,
            limit=args.limit,
            collections=tuple(args.collection),
            types=tuple(args.types),
            statuses=tuple(args.status),
            tags=tuple(args.tag),
            fields=tuple(args.fields),
            explain=args.explain,
            unbounded=args.unbounded,
        )
        response = execute_find(request)
    except ValueError as error:
        parser.error(str(error))

    if args.format == "json":
        print(json.dumps(response.as_dict(), indent=2, ensure_ascii=False))
    else:
        _print_text(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
