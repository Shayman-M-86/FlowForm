#!/usr/bin/env python3
"""Shared documentation model, front-matter parser, and glob matching.

This module is the single place that understands the shape of a FlowForm
documentation file, so every other tool in ``docsys`` sees documents the same
way. It is intentionally dependency-free (no PyYAML): it parses the canonical
front-matter shape used across ``docs/`` — the same shape the existing
``scripts/docs/validate-doc-*.py`` validators parse — extended with the
optional tooling fields described in the documentation model:

- ``related_code``    list of repo paths, directories, or globs (relative to
                      the document) that own the claims in the document
- ``change_triggers`` optional extra paths/globs that should flag the document
                      for review even if not in ``related_code``
- ``exclusions``      optional paths/globs to subtract from the matched set
- ``code_confidence`` optional ``high|medium|low`` hint used to weight impact

All path fields are resolved relative to the document's own directory (matching
the existing ``related_docs`` / relative-link convention), then normalised to
repo-relative POSIX strings so downstream tools can compare them against
``git`` output directly.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

# Resolve the repository root from this file's location:
# scripts/docs/docsys/model.py -> parents[3] is the repo root.
ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs"
GENERATED_DIR = DOCS / "90-generated"
COLLECTIONS = {"project-knowledge", "engineering-workspace"}

# Front-matter vocabulary shared with the validators.
REQUIRED_KEYS = (
    "title",
    "document_type",
    "status",
    "authority",
    "verified_against_commit",
    "aliases",
    "related_code",
    "related_docs",
)
ALLOWED_STATUS = {"scaffold", "draft", "verified"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
TAG_VOCABULARY = {
    "backend",
    "frontend",
    "infrastructure",
    "security",
    "configuration",
    "ci-cd",
    "tooling",
    "meta",
}

_ITEM_RE = re.compile(r'\s+-\s+"?([^"]*?)"?\s*$')
_KV_RE = re.compile(r"([A-Za-z_-]+):\s*(.*)$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_CODE_FENCE_RE = re.compile(r"^```.*?^```", re.M | re.S)
_CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
_WIKI_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def parse_front_matter(text: str) -> dict | None:
    """Parse the canonical front-matter block into a dict.

    Returns ``None`` when the document has no terminated front matter. Scalar
    values become strings (``null`` -> ``None``), block and inline lists become
    lists of strings. This mirrors the existing validators so the tooling and
    the validators never disagree about what a document declares.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm: dict = {}
    current_list: str | None = None
    for line in text[3:end].splitlines():
        if not line.strip():
            continue
        item = _ITEM_RE.match(line)
        if item and current_list is not None:
            fm[current_list].append(item.group(1))
            continue
        kv = _KV_RE.match(line)
        if not kv:
            continue
        key, value = kv.group(1), kv.group(2).strip()
        if value == "":
            fm[key] = []
            current_list = key
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fm[key] = [v.strip().strip('"') for v in inner.split(",")] if inner else []
            current_list = None
        elif value.lower() == "null":
            fm[key] = None
            current_list = None
        else:
            fm[key] = value.strip('"')
            current_list = None
    return fm


def body_after_front_matter(text: str) -> str:
    """Return the Markdown body with any front-matter block removed."""
    if text.startswith("---") and (end := text.find("\n---", 3)) != -1:
        return text[end + 4:]
    return text


def strip_code(body: str) -> str:
    """Remove fenced blocks and inline code so link/heading scans ignore them."""
    return _CODE_SPAN_RE.sub("", _CODE_FENCE_RE.sub("", body))


def extract_headings(body: str) -> list[str]:
    """Return heading texts (levels 1-6) in document order, code stripped."""
    headings = []
    for line in strip_code(body).splitlines():
        m = _HEADING_RE.match(line)
        if m:
            headings.append(m.group(2).strip())
    return headings


def extract_wiki_links(body: str) -> list[str]:
    """Return the note targets referenced by ``[[wiki links]]`` in body order."""
    return [t.strip() for t in _WIKI_LINK_RE.findall(strip_code(body))]


def _repo_relative(path: Path) -> str:
    """Normalise an absolute path to a repo-relative POSIX string."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        # Path escapes the repository; keep it resolved+absolute so callers can
        # still report it, but it will never match repo-relative git output.
        return path.resolve().as_posix()


def resolve_code_pattern(doc_path: Path, pattern: str) -> str:
    """Resolve one ``related_code`` entry to a repo-relative pattern string.

    Entries are written relative to the document's directory (the same
    convention as relative Markdown links and ``related_code`` in existing
    docs). A trailing ``/`` marks a directory prefix; ``*``/``?``/``[`` mark a
    glob. Plain files and directories are normalised the same way. The returned
    string preserves any trailing ``/`` and glob metacharacters so
    :func:`pattern_matches` can interpret them.
    """
    pattern = pattern.strip()
    if not pattern:
        return ""
    had_trailing_slash = pattern.endswith("/")
    # Join relative to the document's directory, then normalise via the repo.
    joined = (doc_path.parent / pattern).resolve()
    rel = _repo_relative(joined)
    if had_trailing_slash and not rel.endswith("/"):
        rel += "/"
    return rel


def pattern_matches(pattern: str, repo_path: str) -> bool:
    """Test whether a repo-relative file path matches a resolved pattern.

    Semantics:
    - trailing ``/``          -> directory prefix match (``a/b/`` matches
                                 ``a/b/c.py`` and ``a/b/deep/c.py``)
    - glob metacharacters     -> ``fnmatch`` against the full path, plus an
                                 implicit ``pattern/**`` directory match so a
                                 glob naming a directory also matches its files
    - plain path              -> exact match, or directory-prefix match if the
                                 pattern names a directory that contains it
    """
    if not pattern:
        return False
    p = PurePosixPath(repo_path.rstrip("/"))
    target = repo_path
    if pattern.endswith("/"):
        prefix = pattern.rstrip("/")
        return target == prefix or target.startswith(prefix + "/")
    if any(ch in pattern for ch in "*?["):
        if fnmatch.fnmatch(target, pattern):
            return True
        # Treat "dir/*" and "dir/**" as also matching nested files.
        base = pattern.rstrip("*").rstrip("/")
        return bool(base) and (target == base or target.startswith(base + "/"))
    # Plain path: exact file, or a directory that contains the target.
    if target == pattern:
        return True
    return target.startswith(pattern + "/") or str(p) == pattern


@dataclass
class Document:
    """A single documentation file plus its parsed metadata and body.

    ``related_patterns``, ``trigger_patterns``, and ``exclusion_patterns`` are
    already resolved to repo-relative pattern strings, ready for matching
    against git output.
    """

    path: Path
    rel_path: str
    docs_dir: Path
    front_matter: dict
    body: str
    headings: list[str] = field(default_factory=list)
    wiki_links: list[str] = field(default_factory=list)
    related_patterns: list[str] = field(default_factory=list)
    trigger_patterns: list[str] = field(default_factory=list)
    exclusion_patterns: list[str] = field(default_factory=list)

    # --- convenience accessors -------------------------------------------
    @property
    def title(self) -> str:
        return str(self.front_matter.get("title") or "")

    @property
    def document_type(self) -> str:
        return str(self.front_matter.get("document_type") or "")

    @property
    def status(self) -> str:
        return str(self.front_matter.get("status") or "")

    @property
    def authority(self) -> str:
        return str(self.front_matter.get("authority") or "")

    @property
    def tags(self) -> list[str]:
        return list(self.front_matter.get("tags") or [])

    @property
    def related_docs(self) -> list[str]:
        return list(self.front_matter.get("related_docs") or [])

    @property
    def collection(self) -> str:
        """Collection membership derived from the physical tree."""
        relative = self.path.relative_to(self.docs_dir)
        if len(relative.parts) == 1:
            return "root"
        return (
            relative.parts[0]
            if relative.parts[0] in COLLECTIONS
            else "legacy"
        )

    @property
    def is_folder_head(self) -> bool:
        return self.path.name.casefold() == folder_head_path(
            self.path.parent
        ).name.casefold()

    @property
    def verified_against_commit(self) -> str | None:
        v = self.front_matter.get("verified_against_commit")
        return None if v in (None, "", "null") else str(v)

    @property
    def code_confidence(self) -> str:
        c = str(self.front_matter.get("code_confidence") or "").lower()
        return c if c in ALLOWED_CONFIDENCE else "medium"

    @property
    def is_generated(self) -> bool:
        return (
            self.document_type == "generated"
            or "/90-generated/" in f"/{self.rel_path}"
            or "/reference/generated/" in f"/{self.rel_path}"
        )

    def code_matches(self, repo_path: str) -> bool:
        """True when ``repo_path`` is owned by this document.

        A path matches when it hits any ``related_code`` or change-trigger
        pattern and is not removed by an exclusion pattern.
        """
        if any(pattern_matches(x, repo_path) for x in self.exclusion_patterns):
            return False
        patterns = self.related_patterns + self.trigger_patterns
        return any(pattern_matches(p, repo_path) for p in patterns)


def _resolve_patterns(doc_path: Path, values) -> list[str]:
    out = []
    for v in values or []:
        resolved = resolve_code_pattern(doc_path, str(v))
        if resolved:
            out.append(resolved)
    return out


def resolve_docs_root(value: str | Path | None = None) -> Path:
    """Resolve a repository-relative documentation root."""
    if value is None:
        return DOCS
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def generated_dir_for(docs_dir: Path) -> Path:
    """Select the generated-output area for the legacy or collection model."""
    docs_dir = docs_dir.resolve()
    if (docs_dir / "project-knowledge").exists():
        return docs_dir / "project-knowledge" / "reference" / "generated"
    return docs_dir / "90-generated"


def folder_head_path(directory: Path) -> Path:
    """Return the convention-based head path for a documentation directory."""
    return directory / f"{directory.name}-index.md"


def load_document(path: Path, docs_dir: Path = DOCS) -> Document | None:
    """Load and fully parse a single documentation file.

    Returns ``None`` for files without valid front matter, so callers can skip
    non-document Markdown without special-casing it.
    """
    text = path.read_text(errors="replace")
    fm = parse_front_matter(text)
    if fm is None:
        return None
    body = body_after_front_matter(text)
    rel = path.resolve().relative_to(ROOT).as_posix()
    return Document(
        path=path,
        rel_path=rel,
        docs_dir=docs_dir.resolve(),
        front_matter=fm,
        body=body,
        headings=extract_headings(body),
        wiki_links=extract_wiki_links(body),
        related_patterns=_resolve_patterns(path, fm.get("related_code")),
        trigger_patterns=_resolve_patterns(path, fm.get("change_triggers")),
        exclusion_patterns=_resolve_patterns(path, fm.get("exclusions")),
    )


class DocSet:
    """An in-memory view of every documentation file under ``docs/``.

    Loads all documents once and offers title/path lookups and the wiki-link
    graph. Every higher-level tool builds on this so the parse cost is paid a
    single time per invocation.
    """

    def __init__(
        self,
        docs: list[Document],
        docs_dir: Path = DOCS,
        unparsed_paths: list[Path] | None = None,
    ):
        self.docs = docs
        self.docs_dir = docs_dir.resolve()
        self.unparsed_paths = list(unparsed_paths or [])
        self._by_rel = {d.rel_path: d for d in docs}
        self._by_abs = {d.path.resolve(): d for d in docs}
        self._by_title = {}
        stem_counts: dict[str, int] = {}
        for d in docs:
            key = d.path.stem.casefold()
            stem_counts[key] = stem_counts.get(key, 0) + 1
        self._by_wiki_target = {}
        for d in docs:
            if d.title:
                self._by_title[d.title.casefold()] = d
            target = (
                d.path.stem
                if stem_counts[d.path.stem.casefold()] == 1
                else d.path.relative_to(self.docs_dir).with_suffix("").as_posix()
            )
            self._by_wiki_target[target.casefold()] = d

    @classmethod
    def load(cls, docs_dir: Path = DOCS) -> "DocSet":
        docs_dir = docs_dir.resolve()
        docs = []
        unparsed_paths = []
        for path in sorted(docs_dir.rglob("*.md")):
            doc = load_document(path, docs_dir)
            if doc is not None:
                docs.append(doc)
            else:
                unparsed_paths.append(path)
        return cls(docs, docs_dir, unparsed_paths)

    @property
    def uses_collection_model(self) -> bool:
        return any((self.docs_dir / name).is_dir() for name in COLLECTIONS)

    def by_title(self, title: str) -> Document | None:
        return self._by_title.get(title.casefold())

    def by_rel(self, rel_path: str) -> Document | None:
        return self._by_rel.get(rel_path)

    def resolve_wiki(self, target: str) -> Document | None:
        return self._by_wiki_target.get(target.casefold())

    def inferred_parent(self, doc: Document) -> Document | None:
        """Infer the nearest structural parent from directory heads."""
        if doc.path.parent == self.docs_dir and doc.is_folder_head:
            return None
        directory = doc.path.parent.parent if doc.is_folder_head else doc.path.parent
        while directory == self.docs_dir or self.docs_dir in directory.parents:
            parent = self._by_abs.get(folder_head_path(directory).resolve())
            if parent is not None and parent.rel_path != doc.rel_path:
                return parent
            if directory == self.docs_dir:
                break
            directory = directory.parent
        return None

    def children(self, doc: Document) -> list[Document]:
        """Return immediate structural children in stable path order."""
        return [
            candidate
            for candidate in self.docs
            if (parent := self.inferred_parent(candidate)) is not None
            and parent.rel_path == doc.rel_path
        ]

    def neighbours(self, doc: Document) -> list[Document]:
        """Documents connected to ``doc`` by wiki links or related_docs.

        The link graph is treated as undirected: both outgoing links and
        documents that link back to ``doc`` are returned, de-duplicated and in
        a stable order.
        """
        seen: dict[str, Document] = {}
        for target in doc.wiki_links:
            n = self.resolve_wiki(target)
            if n and n.rel_path != doc.rel_path:
                seen[n.rel_path] = n
        for title in doc.related_docs:
            n = self.by_title(title)
            if n and n.rel_path != doc.rel_path:
                seen[n.rel_path] = n
        for other in self.docs:
            if other.rel_path == doc.rel_path:
                continue
            links_here = any(
                linked is not None and linked.rel_path == doc.rel_path
                for linked in (self.resolve_wiki(t) for t in other.wiki_links)
            )
            related_here = doc.title.casefold() in {
                t.casefold() for t in other.related_docs
            }
            if links_here or related_here:
                seen.setdefault(other.rel_path, other)
        return list(seen.values())

    def documents_for_code(self, repo_paths) -> dict[str, list[Document]]:
        """Map each changed repo path to the documents that own it."""
        result: dict[str, list[Document]] = {}
        for repo_path in repo_paths:
            matched = [d for d in self.docs if d.code_matches(repo_path)]
            if matched:
                result[repo_path] = matched
        return result
