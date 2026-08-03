"""Compact discovery and retrieval contracts shared by Docsys front ends."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .core.model import HEADING_RE, ROOT, DocSet, Document, strip_code

DEFAULT_FIND_LIMIT = 3
MAX_FIND_LIMIT = 20
DEFAULT_READ_CHARS = 4_000
MAX_READ_CHARS = 12_000
MAX_CODE_PATHS = 10

MATCH_MODES = frozenset({"all", "any", "phrase"})
SEARCH_FIELDS = frozenset(
    {"title", "path", "heading", "tag", "related-code", "body"}
)

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_SIGNIFICANT_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "for",
        "from",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
)
_STATUS_TIE_BREAK = {"verified": 2, "draft": 1, "scaffold": 0}


def _normalise_text(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(value.casefold()))


def _query_terms(value: str) -> tuple[str, ...]:
    tokens = tuple(_TOKEN_RE.findall(value.casefold()))
    significant = tuple(
        token for token in tokens if token not in _SIGNIFICANT_STOP_WORDS
    )
    return significant or tokens


def _normalise_choice_values(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            value.strip().casefold() for value in values if value.strip()
        )
    )


def _normalise_repo_path(value: str, *, label: str) -> str:
    raw = value.strip().replace("\\", "/")
    if not raw:
        raise ValueError(f"{label} must not be empty")
    if raw.startswith("/") or re.match(r"^[A-Za-z]:/", raw):
        raise ValueError(f"{label} must be repository-relative")
    if raw.endswith("/") or any(char in raw for char in "*?["):
        raise ValueError(f"{label} must name one exact file")
    path = PurePosixPath(raw)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{label} must be a normalized repository path")
    resolved = ROOT.joinpath(*path.parts)
    if resolved.is_dir():
        raise ValueError(f"{label} must name one exact file, not a directory")
    return path.as_posix()


def _normalise_scope(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip().replace("\\", "/").rstrip("/")
    if not raw:
        raise ValueError("scope must not be empty")
    if raw.startswith("/") or re.match(r"^[A-Za-z]:/", raw):
        raise ValueError("scope must be repository-relative")
    if any(char in raw for char in "*?["):
        raise ValueError("scope must be a literal documentation path prefix")
    path = PurePosixPath(raw)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("scope must be a normalized documentation path prefix")
    return path.as_posix()


def _summary(doc: Document, max_chars: int = 200) -> str:
    configured = doc.front_matter.get("summary")
    if configured:
        text = " ".join(str(configured).split())
    else:
        paragraphs: list[str] = []
        current: list[str] = []
        for raw_line in strip_code(doc.body).splitlines():
            line = raw_line.strip()
            if line.startswith("#"):
                if current:
                    break
                continue
            if not line:
                if current:
                    break
                continue
            current.append(line)
        if current:
            paragraphs.append(" ".join(current))
        text = " ".join(paragraphs).strip()
    text = re.sub(r"^(?:>\s*|[-*]\s+)", "", text)
    first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
    if first_sentence:
        text = first_sentence
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


class FindRequest(BaseModel):
    """Validated inputs for a bounded documentation search."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    query: str = ""
    scope: str | None = None
    code_paths: tuple[str, ...] = ()
    match: Literal["all", "any", "phrase"] = "all"
    limit: int = Field(default=DEFAULT_FIND_LIMIT, ge=1, le=MAX_FIND_LIMIT)
    collections: tuple[str, ...] = ()
    types: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    explain: bool = False
    unbounded: bool = False

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        return value.strip()

    @field_validator("scope")
    @classmethod
    def _validate_scope(cls, value: str | None) -> str | None:
        return _normalise_scope(value)

    @field_validator("match", mode="before")
    @classmethod
    def _validate_match(cls, value: object) -> object:
        return value.casefold() if isinstance(value, str) else value

    @field_validator("code_paths")
    @classmethod
    def _validate_code_paths(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) > MAX_CODE_PATHS:
            raise ValueError(f"at most {MAX_CODE_PATHS} code paths may be supplied")
        return tuple(
            dict.fromkeys(
                _normalise_repo_path(value, label="code path") for value in values
            )
        )

    @field_validator("collections", "types", "statuses", "tags", "fields")
    @classmethod
    def _validate_choices(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalise_choice_values(values)

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, fields: tuple[str, ...]) -> tuple[str, ...]:
        unknown_fields = sorted(set(fields) - SEARCH_FIELDS)
        if unknown_fields:
            raise ValueError(f"unknown search field: {unknown_fields[0]}")
        return fields

    @model_validator(mode="after")
    def _require_query_or_code_path(self) -> "FindRequest":
        if not self.query and not self.code_paths:
            raise ValueError("provide search terms or at least one --code path")
        return self


@dataclass(frozen=True)
class FindItem:
    path: str
    title: str
    status: str
    summary: str
    score: float | None = None
    matched_terms: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    snippet: str | None = None

    def as_dict(self, *, explain: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {
            "path": self.path,
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
        }
        if explain:
            result.update(
                {
                    "score": self.score,
                    "matched_terms": list(self.matched_terms),
                    "reasons": list(self.reasons),
                    "snippet": self.snippet or "",
                }
            )
        return result


@dataclass(frozen=True)
class FindResponse:
    items: tuple[FindItem, ...]
    total: int
    truncated: bool
    warning: str | None = None
    explain: bool = False

    @property
    def returned(self) -> int:
        return len(self.items)

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "items": [item.as_dict(explain=self.explain) for item in self.items],
            "total": self.total,
            "returned": self.returned,
            "truncated": self.truncated,
        }
        if self.warning:
            result["warning"] = self.warning
        return result

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), separators=(",", ":"), ensure_ascii=False)


class ReadRequest(BaseModel):
    """Validated inputs for exact, bounded documentation retrieval."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    path: str
    section: str | None = None
    include_body: bool = False
    offset: int = Field(default=0, ge=0)
    max_chars: int = Field(default=DEFAULT_READ_CHARS, ge=1, le=MAX_READ_CHARS)
    include_related: bool = False
    include_metadata: bool = False

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        raw_path = value.strip().replace("\\", "/")
        if not raw_path:
            raise ValueError("path must not be empty")
        if raw_path.startswith("/") or re.match(r"^[A-Za-z]:/", raw_path):
            raise ValueError("path must be repository-relative")
        path = PurePosixPath(raw_path)
        if any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("path must be a normalized repository path")
        if path.suffix.casefold() != ".md":
            raise ValueError("path must name a Markdown document")
        return path.as_posix()

    @field_validator("section")
    @classmethod
    def _validate_section(cls, value: str | None) -> str | None:
        if value is None:
            return None
        section = value.strip()
        if not section:
            raise ValueError("section must not be empty")
        return section


@dataclass(frozen=True)
class ReadResponse:
    path: str
    title: str
    status: str
    summary: str
    headings: tuple[str, ...]
    content: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    truncated: bool = False
    next_offset: int | None = None
    related: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "path": self.path,
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "headings": list(self.headings),
        }
        if self.content is not None:
            result.update(
                {
                    "content": self.content,
                    "start_line": self.start_line,
                    "end_line": self.end_line,
                    "truncated": self.truncated,
                    "next_offset": self.next_offset,
                }
            )
        if self.related:
            result["related"] = list(self.related)
        if self.metadata is not None:
            result["metadata"] = self.metadata
        return result

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), separators=(",", ":"), ensure_ascii=False)


@dataclass
class _Candidate:
    doc: Document
    score: float
    matched_terms: set[str] = field(default_factory=set)
    reasons: list[str] = field(default_factory=list)
    snippet: str = ""


def _scope_matches(doc: Document, scope: str | None) -> bool:
    if not scope:
        return True
    paths = {doc.rel_path}
    try:
        paths.add(doc.path.relative_to(doc.docs_dir).as_posix())
    except ValueError:
        pass
    return any(path == scope or path.startswith(scope + "/") for path in paths)


def _filter_matches(doc: Document, request: FindRequest) -> bool:
    if not _scope_matches(doc, request.scope):
        return False
    if request.collections and doc.collection.casefold() not in request.collections:
        return False
    if request.types and doc.document_type.casefold() not in request.types:
        return False
    if request.statuses and doc.status.casefold() not in request.statuses:
        return False
    doc_tags = {tag.casefold() for tag in doc.tags}
    if request.tags and not doc_tags.intersection(request.tags):
        return False
    if request.code_paths and not set(doc.related_patterns).intersection(
        request.code_paths
    ):
        return False
    return True


def _field_values(doc: Document) -> dict[str, list[str]]:
    aliases = doc.front_matter.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]
    return {
        "title": [doc.title, *(str(alias) for alias in aliases)],
        "path": [doc.rel_path],
        "heading": list(doc.headings),
        "tag": list(doc.tags),
        "related-code": list(doc.related_patterns),
        "body": [strip_code(doc.body)],
    }


def _body_snippet(doc: Document, terms: tuple[str, ...]) -> str:
    text = " ".join(strip_code(doc.body).split())
    lowered = text.casefold()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    start = max(0, min(positions) - 60) if positions else 0
    end = min(len(text), start + 180)
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def _score_document(doc: Document, request: FindRequest) -> _Candidate | None:
    if not _filter_matches(doc, request):
        return None

    terms = _query_terms(request.query)
    phrase = _normalise_text(request.query)
    enabled = request.fields or tuple(sorted(SEARCH_FIELDS))
    values = _field_values(doc)
    normalised = {
        name: [_normalise_text(value) for value in field_values]
        for name, field_values in values.items()
        if name in enabled
    }
    token_sets = {
        name: [set(_TOKEN_RE.findall(value)) for value in field_values]
        for name, field_values in normalised.items()
    }

    term_fields: dict[str, set[str]] = {term: set() for term in terms}
    for term in terms:
        for field_name, field_token_sets in token_sets.items():
            if any(term in tokens for tokens in field_token_sets):
                term_fields[term].add(field_name)

    if terms:
        if request.match == "all" and any(
            not fields for fields in term_fields.values()
        ):
            return None
        if request.match == "any" and not any(term_fields.values()):
            return None
        if request.match == "phrase" and not any(
            phrase and phrase in value
            for field_values in normalised.values()
            for value in field_values
        ):
            return None

    weights = {
        "title": 50.0,
        "path": 45.0,
        "heading": 30.0,
        "tag": 25.0,
        "related-code": 25.0,
        "body": 5.0,
    }
    score = 0.0
    reasons: list[str] = []
    for field_name in enabled:
        matched_here = sum(
            1 for term in terms if field_name in term_fields.get(term, set())
        )
        if not matched_here:
            continue
        score += weights[field_name] * matched_here
        reasons.append(f"{field_name} match")
        if field_name == "body":
            body_tokens = _TOKEN_RE.findall(normalised["body"][0])
            for term in terms:
                frequency = body_tokens.count(term)
                if frequency > 1:
                    score += math.log(frequency)

    title_alias_values = normalised.get("title", [])
    path_values = normalised.get("path", [])
    if phrase and phrase in title_alias_values:
        score += 100.0
        reasons.insert(0, "exact title or alias match")
    elif phrase and phrase in path_values:
        score += 90.0
        reasons.insert(0, "exact path match")
    elif request.match == "phrase":
        score += 20.0
        reasons.insert(0, "phrase match")

    if request.code_paths:
        score += 80.0
        reasons.insert(0, "exact related_code match")

    matched_terms = {term for term, fields in term_fields.items() if fields}
    return _Candidate(
        doc=doc,
        score=score,
        matched_terms=matched_terms,
        reasons=list(dict.fromkeys(reasons)),
        snippet=_body_snippet(doc, tuple(matched_terms)),
    )


def execute_find(
    request: FindRequest,
    docset: DocSet | None = None,
) -> FindResponse:
    """Execute a validated find request with compact result projection."""
    docset = docset or DocSet.load()
    candidates = [
        candidate
        for doc in docset.docs
        if (candidate := _score_document(doc, request)) is not None
    ]
    candidates.sort(
        key=lambda item: (
            -item.score,
            -_STATUS_TIE_BREAK.get(item.doc.status, -1),
            item.doc.rel_path,
        )
    )

    total = len(candidates)
    selected = candidates if request.unbounded else candidates[: request.limit]
    items = tuple(
        FindItem(
            path=item.doc.rel_path,
            title=item.doc.title,
            status=item.doc.status,
            summary=_summary(item.doc),
            score=round(item.score, 3),
            matched_terms=tuple(sorted(item.matched_terms)),
            reasons=tuple(item.reasons),
            snippet=item.snippet,
        )
        for item in selected
    )
    unreliable = sum(item.status != "verified" for item in items)
    warning = None
    if unreliable:
        noun = "document is" if unreliable == 1 else "documents are"
        warning = f"{unreliable} returned {noun} not verified and current."
    return FindResponse(
        items=items,
        total=total,
        truncated=len(items) < total,
        warning=warning,
        explain=request.explain,
    )


def _section_source(body: str, requested: str) -> tuple[str, int]:
    target = requested.strip().casefold()
    lines = body.splitlines(keepends=True)
    start: int | None = None
    level: int | None = None
    in_fence = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line.rstrip("\r\n"))
        if not match:
            continue
        current_level = len(match.group(1))
        heading = match.group(2).strip()
        if start is None:
            if heading.casefold() == target:
                start = index
                level = current_level
            continue
        if level is not None and current_level <= level:
            return (
                "".join(lines[start:index]).rstrip(),
                sum(len(line) for line in lines[:start]),
            )
    if start is None:
        raise ValueError(f"section not found: {requested}")
    return (
        "".join(lines[start:]).rstrip(),
        sum(len(line) for line in lines[:start]),
    )


def _direct_related_paths(doc: Document, docset: DocSet) -> tuple[str, ...]:
    paths: dict[str, None] = {}
    for target in doc.wiki_links:
        related = docset.resolve_wiki(target)
        if related is not None and related.rel_path != doc.rel_path:
            paths[related.rel_path] = None
    for title in doc.related_docs:
        related = docset.by_title(title)
        if related is not None and related.rel_path != doc.rel_path:
            paths[related.rel_path] = None
    return tuple(paths)


def execute_read(
    request: ReadRequest,
    docset: DocSet | None = None,
) -> ReadResponse:
    """Read one exact document path, returning body content only on request."""
    docset = docset or DocSet.load()
    doc = docset.by_rel(request.path)
    if doc is None:
        raise ValueError(f"document not found: {request.path}")

    content: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    truncated = False
    next_offset: int | None = None
    if request.section is not None or request.include_body:
        source, source_offset = (
            _section_source(doc.body, request.section)
            if request.section is not None
            else (doc.body, 0)
        )
        content = source[request.offset : request.offset + request.max_chars]
        truncated = request.offset + len(content) < len(source)
        if truncated:
            next_offset = request.offset + len(content)
        if content:
            absolute_start = source_offset + request.offset
            absolute_end = absolute_start + len(content) - 1
            start_line = doc.body_start_line + doc.body[:absolute_start].count("\n")
            end_line = doc.body_start_line + doc.body[:absolute_end].count("\n")

    return ReadResponse(
        path=doc.rel_path,
        title=doc.title,
        status=doc.status,
        summary=_summary(doc),
        headings=tuple(doc.headings),
        content=content,
        start_line=start_line,
        end_line=end_line,
        truncated=truncated,
        next_offset=next_offset,
        related=_direct_related_paths(doc, docset) if request.include_related else (),
        metadata=dict(doc.front_matter) if request.include_metadata else None,
    )
