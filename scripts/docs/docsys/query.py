#!/usr/bin/env python3
"""Deterministic documentation query engine.

Ranks documents against a free-text query using explainable, weighted field
matches — no embeddings, no network, no non-determinism. Semantic search can be
layered on later, but deterministic retrieval is preferred first so results are
reproducible and debuggable.

Signals and their weights (a hit in a higher-signal field outranks a body hit):

    title match             5.0 per term (x2 for a whole-phrase title hit)
    heading match           3.0 per term
    tag match               2.5 per term
    related_code match      2.0 per term (path/basename tokens)
    body match              1.0 per term (log-damped by frequency)
    document_type / author  1.5 when a term equals the type/authority

Verification status and authority act as tie-breaking multipliers: a
``verified`` canonical document ranks above a ``scaffold`` on equal text
evidence, because it carries real claims. Wiki-link relationships contribute a
small boost when a matched document is linked from other matched documents
(central documents surface first).

    python3 -m docsys query "response encryption locator"
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field

from .model import DocSet, Document, strip_code

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")

_STATUS_MULT = {"verified": 1.25, "draft": 1.05, "scaffold": 0.7}
_AUTHORITY_MULT = {"canonical": 1.15, "reference": 1.05}

W_TITLE = 5.0
W_HEADING = 3.0
W_TAG = 2.5
W_TYPE = 1.5
W_CODE = 2.0
W_BODY = 1.0


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _path_tokens(patterns: list[str]) -> set[str]:
    toks: set[str] = set()
    for p in patterns:
        for seg in re.split(r"[/._\-]", p):
            if seg and not any(ch in seg for ch in "*?["):
                toks.add(seg.lower())
    return toks


@dataclass
class ScoredDoc:
    doc: Document
    score: float
    matched_terms: set[str] = field(default_factory=set)
    reasons: list[str] = field(default_factory=list)
    snippet: str = ""

    def as_dict(self) -> dict:
        return {
            "path": self.doc.rel_path,
            "title": self.doc.title,
            "document_type": self.doc.document_type,
            "authority": self.doc.authority,
            "status": self.doc.status,
            "tags": sorted(self.doc.tags),
            "score": round(self.score, 3),
            "matched_terms": sorted(self.matched_terms),
            "reasons": self.reasons,
            "snippet": self.snippet,
        }


class QueryEngine:
    """Precomputes per-document token frequencies for fast repeated queries."""

    def __init__(self, docset: DocSet):
        self.docset = docset
        self._body_tokens: dict[str, dict[str, int]] = {}
        self._title_tokens: dict[str, set[str]] = {}
        self._heading_tokens: dict[str, set[str]] = {}
        self._code_tokens: dict[str, set[str]] = {}
        self._backlink_count: dict[str, int] = {}
        for d in docset.docs:
            body = strip_code(d.body).lower()
            freqs: dict[str, int] = {}
            for tok in tokenize(body):
                freqs[tok] = freqs.get(tok, 0) + 1
            self._body_tokens[d.rel_path] = freqs
            self._title_tokens[d.rel_path] = set(tokenize(d.title))
            htoks: set[str] = set()
            for h in d.headings:
                htoks.update(tokenize(h))
            self._heading_tokens[d.rel_path] = htoks
            self._code_tokens[d.rel_path] = _path_tokens(
                d.related_patterns + d.trigger_patterns
            )
        for d in docset.docs:
            for n in docset.neighbours(d):
                self._backlink_count[n.rel_path] = (
                    self._backlink_count.get(n.rel_path, 0) + 1
                )

    def _snippet(self, doc: Document, terms: set[str]) -> str:
        text = strip_code(doc.body)
        lowered = text.lower()
        for term in terms:
            i = lowered.find(term)
            if i != -1:
                start = max(0, i - 60)
                end = min(len(text), i + 80)
                frag = " ".join(text[start:end].split())
                return ("…" if start else "") + frag + ("…" if end < len(text) else "")
        # Fallback: first non-empty prose line.
        for line in text.splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                return " ".join(s.split())[:140]
        return ""

    def search(
        self,
        query: str,
        limit: int = 10,
        doc_type: str | None = None,
        tag: str | None = None,
        min_status: str | None = None,
    ) -> list[ScoredDoc]:
        terms = set(tokenize(query))
        phrase = query.strip().lower()
        results: list[ScoredDoc] = []
        status_rank = {"scaffold": 0, "draft": 1, "verified": 2}

        for doc in self.docset.docs:
            if doc_type and doc.document_type != doc_type:
                continue
            if tag and tag not in doc.tags:
                continue
            if min_status and status_rank.get(doc.status, 0) < status_rank.get(
                min_status, 0
            ):
                continue

            rel = doc.rel_path
            score = 0.0
            matched: set[str] = set()
            reasons: list[str] = []

            title_toks = self._title_tokens[rel]
            head_toks = self._heading_tokens[rel]
            code_toks = self._code_tokens[rel]
            body_freqs = self._body_tokens[rel]
            tag_set = {t.lower() for t in doc.tags}

            for term in terms:
                if term in title_toks:
                    score += W_TITLE
                    matched.add(term)
                if term in head_toks:
                    score += W_HEADING
                    matched.add(term)
                if term in tag_set:
                    score += W_TAG
                    matched.add(term)
                if term in code_toks:
                    score += W_CODE
                    matched.add(term)
                if term == doc.document_type.lower() or term == doc.authority.lower():
                    score += W_TYPE
                    matched.add(term)
                freq = body_freqs.get(term, 0)
                if freq:
                    score += W_BODY * (1 + math.log(freq))
                    matched.add(term)

            if not matched:
                continue

            # Whole-phrase title hit is a strong exact-match signal.
            if phrase and phrase == doc.title.lower():
                score += W_TITLE * 2
                reasons.append("exact title match")
            elif title_toks & terms:
                reasons.append("title term match")
            if head_toks & terms:
                reasons.append("heading match")
            if tag_set & terms:
                reasons.append("tag match")
            if code_toks & terms:
                reasons.append("related_code term match")

            # Coverage bonus: matching more of the query is better.
            coverage = len(matched) / max(1, len(terms))
            score *= 0.5 + 0.5 * coverage

            # Status/authority multipliers reward documents with real claims.
            score *= _STATUS_MULT.get(doc.status, 1.0)
            score *= _AUTHORITY_MULT.get(doc.authority, 1.0)

            # Small centrality boost for well-connected documents.
            backlinks = self._backlink_count.get(rel, 0)
            score *= 1 + min(0.15, 0.03 * backlinks)

            results.append(
                ScoredDoc(
                    doc,
                    score,
                    matched,
                    reasons,
                    self._snippet(doc, matched),
                )
            )

        results.sort(key=lambda r: (-r.score, r.doc.rel_path))
        return results[:limit]


def search(query: str, limit: int = 10, **kwargs) -> list[ScoredDoc]:
    engine = QueryEngine(DocSet.load())
    return engine.search(query, limit=limit, **kwargs)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="docsys query")
    parser.add_argument("query", nargs="+", help="search terms")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--type", dest="doc_type", help="filter by document_type")
    parser.add_argument("--tag", help="filter by tag")
    parser.add_argument(
        "--min-status",
        choices=["scaffold", "draft", "verified"],
        help="minimum status",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    results = search(
        " ".join(args.query),
        limit=args.limit,
        doc_type=args.doc_type,
        tag=args.tag,
        min_status=args.min_status,
    )
    if args.json:
        print(json.dumps([r.as_dict() for r in results], indent=2))
        return 0
    if not results:
        print("no matching documents")
        return 0
    for r in results:
        print(f"{r.score:6.2f}  {r.doc.title}  [{r.doc.status}]")
        print(f"        {r.doc.rel_path}")
        if r.reasons:
            print(f"        {', '.join(r.reasons)}")
        if r.snippet:
            print(f"        {r.snippet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
