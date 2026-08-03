#!/usr/bin/env python3
"""Exact, bounded retrieval for ``docsys read``."""

from __future__ import annotations

import argparse
import json

from ..contracts import ReadRequest, execute_read
from ..core.model import DocSet, Document


def _brief(doc: Document) -> dict:
    return {
        "path": doc.rel_path,
        "title": doc.title,
        "document_type": doc.document_type,
        "status": doc.status,
        "authority": doc.authority,
        "collection": doc.collection,
    }


def get_document(
    identifier: str, docset: DocSet | None = None, include_body: bool = True
) -> dict | None:
    """Fetch a document by title (preferred) or repo-relative path."""
    docset = docset or DocSet.load()
    doc = docset.by_title(identifier) or docset.by_rel(identifier)
    if doc is None:
        return None
    result = {
        **_brief(doc),
        "tags": sorted(doc.tags),
        "verified_evidence_digest": doc.verified_evidence_digest,
        "last_edited": doc.last_edited,
        "related_code": list(doc.front_matter.get("related_code") or []),
        "related_code_resolved": list(doc.related_patterns),
        "related_docs": list(doc.related_docs),
        "headings": list(doc.headings),
    }
    if include_body:
        result["body"] = doc.body
    return result


def get_related(identifier: str, docset: DocSet | None = None) -> dict | None:
    """Fetch the neighbouring documents (wiki links + backlinks) of a document."""
    docset = docset or DocSet.load()
    doc = docset.by_title(identifier) or docset.by_rel(identifier)
    if doc is None:
        return None
    return {
        "document": _brief(doc),
        "related_documents": [_brief(n) for n in docset.neighbours(doc)],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docsys read",
        description="Read one exact documentation path.",
    )
    parser.add_argument("path", help="exact path returned by docsys find")
    parser.add_argument("--section", help="one exact Markdown heading")
    parser.add_argument(
        "--body",
        action="store_true",
        help="include bounded document body content",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        metavar="N",
        help="character offset for body or section content",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=4_000,
        metavar="N",
        help="content limit, 1-12000 (default: 4000)",
    )
    parser.add_argument(
        "--related",
        action="store_true",
        help="include direct outgoing document paths",
    )
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="include complete front matter",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format (default: text)",
    )
    return parser


def _print_text(response) -> None:
    print(f"[{response.status}] {response.path} — {response.title}")
    if response.summary:
        print(response.summary)
    if response.headings:
        print("headings:")
        for heading in response.headings:
            print(f"- {heading}")
    if response.content is not None:
        print()
        if response.start_line is not None:
            print(f"lines: {response.start_line}-{response.end_line}")
        print(response.content)
        if response.truncated:
            print()
            print(f"truncated; continue with --offset {response.next_offset}")
    if response.related:
        print("related:")
        for path in response.related:
            print(f"- {path}")
    if response.metadata is not None:
        print("metadata:")
        print(json.dumps(response.metadata, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        request = ReadRequest(
            path=args.path,
            section=args.section,
            include_body=args.body,
            offset=args.offset,
            max_chars=args.max_chars,
            include_related=args.related,
            include_metadata=args.metadata,
        )
        response = execute_read(request)
    except ValueError as error:
        parser.error(str(error))

    if args.format == "json":
        print(json.dumps(response.as_dict(), indent=2, ensure_ascii=False))
    else:
        _print_text(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
