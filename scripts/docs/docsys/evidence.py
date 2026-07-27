#!/usr/bin/env python3
"""Staged evidence digests and verification-state automation.

An authored document cannot contain the SHA of the same commit that contains
that metadata: changing the SHA changes the commit. Docsys therefore verifies
the staged implementation evidence named by ``related_code`` and
``change_triggers`` and records a digest that excludes documentation content.

Commands:

    python3 -m docsys evidence promote --staged docs/path.md [...]
    python3 -m docsys evidence check-staged --sync-invalidations
    python3 -m docsys evidence migrate-commit-baselines
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .model import (
    ROOT,
    DocSet,
    Document,
    load_document,
    load_document_text,
    pattern_matches,
)

DIGEST_PREFIX = "sha256:"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STATUS_RE = re.compile(r"(?m)^status:\s*.*$")
_DIGEST_RE = re.compile(r"(?m)^verified_evidence_digest:\s*.*$")
_LEGACY_RE = re.compile(r"(?m)^verified_against_commit:\s*(.*)$")


def _git_bytes(args: list[str]) -> bytes:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.decode(errors="replace").strip()
            or f"git {' '.join(args)} failed"
        )
    return proc.stdout


def _git_text(args: list[str]) -> str:
    return _git_bytes(args).decode(errors="replace")


@dataclass(frozen=True)
class EvidenceEntry:
    path: str
    mode: str
    object_id: str


@dataclass(frozen=True)
class EvidenceSnapshot:
    digest: str
    files: tuple[str, ...]


@dataclass
class EvidenceSource:
    """One immutable Git snapshot used to calculate document evidence."""

    entries: dict[str, EvidenceEntry]
    label: str

    @classmethod
    def from_index(cls) -> "EvidenceSource":
        entries: dict[str, EvidenceEntry] = {}
        for record in _git_bytes(["ls-files", "-s", "-z"]).split(b"\0"):
            if not record:
                continue
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_id, stage = metadata.decode().split()
            if stage != "0":
                raise RuntimeError(
                    "cannot calculate staged evidence with unresolved Git conflicts"
                )
            path = raw_path.decode(errors="surrogateescape")
            entries[path] = EvidenceEntry(path, mode, object_id)
        return cls(entries, "staged index")

    @classmethod
    def from_ref(cls, ref: str = "HEAD") -> "EvidenceSource":
        entries: dict[str, EvidenceEntry] = {}
        for record in _git_bytes(["ls-tree", "-r", "-z", ref]).split(b"\0"):
            if not record:
                continue
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode().split()
            if object_type != "blob":
                continue
            path = raw_path.decode(errors="surrogateescape")
            entries[path] = EvidenceEntry(path, mode, object_id)
        return cls(entries, ref)

    def snapshot(self, doc: Document) -> EvidenceSnapshot:
        hasher = hashlib.sha256()

        declarations = (
            ("related_code", doc.related_patterns),
            ("change_triggers", doc.trigger_patterns),
            ("exclusions", doc.exclusion_patterns),
        )
        for kind, patterns in declarations:
            for pattern in sorted(patterns):
                hasher.update(f"{kind}\0{pattern}\n".encode())

        matched: list[EvidenceEntry] = []
        patterns = doc.related_patterns + doc.trigger_patterns
        for path, entry in self.entries.items():
            if any(pattern_matches(pattern, path) for pattern in doc.exclusion_patterns):
                continue
            if any(pattern_matches(pattern, path) for pattern in patterns):
                matched.append(entry)

        for entry in sorted(matched, key=lambda item: item.path):
            hasher.update(
                f"blob\0{entry.path}\0{entry.mode}\0{entry.object_id}\n".encode()
            )

        return EvidenceSnapshot(
            digest=DIGEST_PREFIX + hasher.hexdigest(),
            files=tuple(entry.path for entry in sorted(matched, key=lambda item: item.path)),
        )


def _set_metadata(path: Path, *, status: str, digest: str | None) -> None:
    text = path.read_text()
    digest_value = digest or "null"
    if not _STATUS_RE.search(text):
        raise ValueError(f"{path.relative_to(ROOT)} has no status field")
    text = _STATUS_RE.sub(f"status: {status}", text, count=1)
    if _DIGEST_RE.search(text):
        text = _DIGEST_RE.sub(
            f"verified_evidence_digest: {digest_value}",
            text,
            count=1,
        )
    elif _LEGACY_RE.search(text):
        text = _LEGACY_RE.sub(
            f"verified_evidence_digest: {digest_value}",
            text,
            count=1,
        )
    else:
        raise ValueError(
            f"{path.relative_to(ROOT)} has no verification metadata field"
        )
    path.write_text(text)


def _repo_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    try:
        path.relative_to((ROOT / "docs").resolve())
    except ValueError as exc:
        raise ValueError(f"verification target must be under docs/: {value}") from exc
    if path.suffix != ".md":
        raise ValueError(f"verification target must be Markdown: {value}")
    return path


def _is_staged(repo_path: str) -> bool:
    staged = set(
        line
        for line in _git_text(["diff", "--cached", "--name-only"]).splitlines()
        if line
    )
    return repo_path in staged


def _has_unstaged(repo_path: str) -> bool:
    proc = subprocess.run(
        ["git", "diff", "--quiet", "--", repo_path],
        cwd=ROOT,
    )
    return proc.returncode != 0


def _load_index_document(doc: Document) -> Document:
    """Return the exact indexed version when the worktree has later edits."""
    try:
        text = _git_text(["show", f":{doc.rel_path}"])
    except RuntimeError:
        return doc
    return load_document_text(doc.path, text, doc.docs_dir) or doc


def promote_staged(values: list[str]) -> int:
    """Promote explicitly reviewed staged documents and record their digest."""
    source = EvidenceSource.from_index()
    promoted: list[str] = []

    for value in values:
        path = _repo_path(value)
        rel = path.relative_to(ROOT).as_posix()
        if not _is_staged(rel):
            raise ValueError(f"stage the document before verification: {rel}")
        if _has_unstaged(rel):
            raise ValueError(
                f"{rel} has unstaged edits; stage a single reviewable version first"
            )
        doc = load_document(path)
        if doc is None:
            raise ValueError(f"{rel} has invalid front matter")
        snapshot = source.snapshot(doc)
        if not snapshot.files and not doc.is_generated:
            raise ValueError(
                f"{rel} resolves no evidence files; correct related_code before verification"
            )
        _set_metadata(path, status="verified", digest=snapshot.digest)
        subprocess.run(["git", "add", "--", rel], cwd=ROOT, check=True)
        promoted.append(rel)

    for rel in promoted:
        print(f"verified {rel} against staged evidence")
    return 0


def check_staged(*, sync_invalidations: bool = False) -> int:
    """Check verified documents against the staged Git snapshot.

    When requested, verified documents invalidated only by staged evidence
    changes are automatically downgraded and staged. The hook then fails once
    so the author can review the added documentation changes.
    """
    source = EvidenceSource.from_index()
    docset = DocSet.load()
    staged_paths = set(
        line
        for line in _git_text(["diff", "--cached", "--name-only"]).splitlines()
        if line
    )
    staged_docs = {
        path for path in staged_paths if path.startswith("docs/") and path.endswith(".md")
    }
    partially_staged = sorted(path for path in staged_docs if _has_unstaged(path))
    if partially_staged:
        for path in partially_staged:
            print(f"verification blocked by unstaged document edits: {path}")
        return 1

    staged_evidence = {
        path for path in staged_paths if not path.startswith("docs/")
    }
    mismatches: list[Document] = []

    for worktree_doc in docset.docs:
        doc = (
            _load_index_document(worktree_doc)
            if worktree_doc.rel_path not in staged_docs
            and _has_unstaged(worktree_doc.rel_path)
            else worktree_doc
        )
        is_impacted = any(doc.code_matches(path) for path in staged_evidence)
        if doc.rel_path not in staged_docs and not is_impacted:
            continue
        if doc.status != "verified":
            continue
        current = doc.verified_evidence_digest
        snapshot = source.snapshot(doc)
        if current != snapshot.digest:
            mismatches.append(doc)

    if not mismatches:
        print("staged documentation evidence is current")
        return 0

    changed: list[str] = []
    blocked: list[str] = []
    for doc in mismatches:
        if not sync_invalidations:
            blocked.append(doc.rel_path)
            continue
        if doc.rel_path in staged_paths or _has_unstaged(doc.rel_path):
            blocked.append(doc.rel_path)
            continue
        _set_metadata(doc.path, status="draft", digest=None)
        subprocess.run(["git", "add", "--", doc.rel_path], cwd=ROOT, check=True)
        changed.append(doc.rel_path)

    for path in changed:
        print(f"downgraded stale documentation to draft: {path}")
    for path in blocked:
        print(
            "verification required: "
            f"{path} does not match its staged evidence digest"
        )

    if changed:
        print("review the automatically staged documentation invalidations")
    return 1


def migrate_commit_baselines() -> int:
    """Replace legacy commit metadata while preserving its evidence baseline."""
    docset = DocSet.load()
    sources: dict[str, EvidenceSource] = {}
    migrated = 0

    for doc in docset.docs:
        if "verified_against_commit" not in doc.front_matter:
            continue
        legacy = doc.front_matter.get("verified_against_commit")
        digest: str | None = None
        if doc.status == "verified" and legacy not in (None, "", "null"):
            ref = str(legacy)
            if ref not in sources:
                sources[ref] = EvidenceSource.from_ref(ref)
            source = sources[ref]
            snapshot = source.snapshot(doc)
            if not snapshot.files and not doc.is_generated:
                raise ValueError(
                    f"{doc.rel_path} resolves no evidence files at {ref}"
                )
            digest = snapshot.digest
        _set_metadata(doc.path, status=doc.status, digest=digest)
        migrated += 1

    print(f"migrated {migrated} documents to evidence digests")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docsys evidence")
    subparsers = parser.add_subparsers(dest="command", required=True)

    promote = subparsers.add_parser(
        "promote",
        help="mark explicitly reviewed staged documents verified",
    )
    promote.add_argument("--staged", action="store_true", required=True)
    promote.add_argument("paths", nargs="+")

    check = subparsers.add_parser(
        "check-staged",
        help="validate verified documents against staged evidence",
    )
    check.add_argument("--sync-invalidations", action="store_true")

    subparsers.add_parser(
        "migrate-commit-baselines",
        help="replace legacy commit metadata using each recorded baseline",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "promote":
            return promote_staged(args.paths)
        if args.command == "check-staged":
            return check_staged(sync_invalidations=args.sync_invalidations)
        return migrate_commit_baselines()
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"documentation evidence error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
