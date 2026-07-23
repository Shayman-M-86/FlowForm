#!/usr/bin/env python3
"""Single-document and related-document retrieval helpers.

These back the MCP ``get_document`` / ``get_related`` operations and are handy
on their own. They return the document body plus resolved metadata so a caller
can load exactly one document instead of the whole tree.
"""

from __future__ import annotations

from .model import DocSet, Document


def _brief(doc: Document) -> dict:
    return {
        "path": doc.rel_path,
        "title": doc.title,
        "document_type": doc.document_type,
        "status": doc.status,
        "authority": doc.authority,
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
        "verified_against_commit": doc.verified_against_commit,
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
