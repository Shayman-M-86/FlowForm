#!/usr/bin/env python3
"""Staged evidence digests and verification-state automation.

An authored document cannot contain the SHA of the same commit that contains
that metadata: changing the SHA changes the commit. Docsys therefore verifies
the staged implementation evidence named by ``related_code`` and
``change_triggers`` and records a digest that excludes documentation content.

Commands:

    tools/bin/docsys evidence promote --staged [--stage] docs/path.md [...]
    tools/bin/docsys evidence sync-last-edited
    tools/bin/docsys evidence check-last-edited
    tools/bin/docsys evidence check-staged
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shlex
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .impact import detect_impact
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
_LAST_EDITED_RE = re.compile(r"(?m)^last_edited:\s*.*$")


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


def _today() -> str:
    return date.today().isoformat()


def _set_last_edited(path: Path, value: str | None = None) -> bool:
    text = path.read_text()
    value = value or _today()
    replacement = f"last_edited: {value}"
    if _LAST_EDITED_RE.search(text):
        updated = _LAST_EDITED_RE.sub(replacement, text, count=1)
    elif _DIGEST_RE.search(text):
        updated = _DIGEST_RE.sub(
            lambda match: f"{match.group(0)}\n{replacement}",
            text,
            count=1,
        )
    else:
        raise ValueError(
            f"{path.relative_to(ROOT)} has no verification metadata field"
        )
    if updated == text:
        return False
    path.write_text(updated)
    return True


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
    else:
        raise ValueError(
            f"{path.relative_to(ROOT)} has no verification metadata field"
        )
    path.write_text(text)
    _set_last_edited(path)


def _repo_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    try:
        path.relative_to((ROOT / "docs").resolve())
    except ValueError as exc:
        raise ValueError(f"verification target must be under docs/: {value}") from exc
    if path.suffix != ".md":
        raise ValueError(f"verification target must be Markdown: {value}")
    return path


def _load_index_document(doc: Document) -> Document:
    """Return the exact indexed version when the worktree has later edits."""
    try:
        text = _git_text(["show", f":{doc.rel_path}"])
    except RuntimeError:
        return doc
    return load_document_text(doc.path, text, doc.docs_dir) or doc


def promote_staged(values: list[str], *, stage: bool = False) -> int:
    """Prepare verified metadata against staged evidence and optionally stage it."""
    source = EvidenceSource.from_index()
    promoted: list[str] = []

    for value in values:
        path = _repo_path(value)
        rel = path.relative_to(ROOT).as_posix()
        doc = load_document(path)
        if doc is None:
            raise ValueError(f"{rel} has invalid front matter")
        if doc.collection != "project-knowledge":
            raise ValueError(
                f"evidence verification is only available for Project Knowledge: {rel}"
            )
        if doc.is_generated:
            raise ValueError(
                f"generated documentation must be regenerated, not promoted: {rel}"
            )
        snapshot = source.snapshot(doc)
        if not snapshot.files and not doc.is_generated:
            raise ValueError(
                f"{rel} resolves no evidence files; correct related_code before verification"
            )
        _set_metadata(path, status="verified", digest=snapshot.digest)
        promoted.append(rel)

    for rel in promoted:
        print(f"prepared verified metadata against staged evidence: {rel}")
    if promoted:
        if stage:
            _git_bytes(["add", "--", *promoted])
            print()
            print(
                "staged updated verified metadata: "
                f"{' '.join(shlex.quote(path) for path in promoted)}"
            )
        else:
            print()
            print("Stage the updated documents, then retry the commit:")
            print(f"  git add -- {' '.join(shlex.quote(path) for path in promoted)}")
    return 0


def check_staged() -> int:
    """Read-only check of verified documents against the staged Git snapshot."""
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
    staged_evidence = {
        path for path in staged_paths if not path.startswith("docs/")
    }
    impact_by_doc = {
        item.doc.rel_path: item
        for item in detect_impact(sorted(staged_evidence), docset)
    }
    mismatches: list[Document] = []

    for worktree_doc in docset.docs:
        doc = _load_index_document(worktree_doc)
        impact = impact_by_doc.get(doc.rel_path)
        if doc.rel_path not in staged_docs and impact is None:
            continue
        if doc.collection != "project-knowledge" or doc.status != "verified":
            continue
        current = doc.verified_evidence_digest
        snapshot = source.snapshot(doc)
        if current == snapshot.digest:
            continue
        if impact is not None and impact.confidence != "high":
            continue
        mismatches.append(doc)

    if not mismatches:
        print("staged documentation evidence is current")
        return 0

    print()
    print("DOCUMENTATION REVIEW REQUIRED — COMMIT STOPPED")
    print(
        "Staged implementation evidence no longer matches these verified "
        "Project Knowledge documents."
    )
    print()
    for doc in mismatches:
        print(
            "verification required: "
            f"{doc.rel_path} does not match its staged evidence digest"
        )

    paths = [doc.rel_path for doc in mismatches]
    quoted_paths = " ".join(shlex.quote(path) for path in paths)
    print()
    print("What to do next:")
    print("  1. Review the affected staged documents:")
    print(f"     git diff --cached -- {quoted_paths}")
    print()
    print("  2. Choose one outcome:")
    print("     - If the documents are still accurate, approve and re-verify them:")
    print(
        "       tools/bin/docsys evidence "
        f"promote --staged --stage {quoted_paths}"
    )
    print(
        "     - If a document is outdated, correct it before promoting."
    )
    print(
        "     - To leave it unverified, set `status: draft` and "
        "`verified_evidence_digest: null`."
    )
    print()
    print("  3. Run the commit again.")
    print()
    print("No files were changed or staged by this check.")
    print()
    print(
        "For a guided review, ask a coding agent to use "
        f"$flowform-doc-verification on: {', '.join(paths)}"
    )
    return 1


def sync_last_edited_staged() -> int:
    """Update working-tree dates for staged docs without staging them."""
    staged_paths = sorted(
        line
        for line in _git_text(["diff", "--cached", "--name-only"]).splitlines()
        if line.startswith("docs/") and line.endswith(".md")
    )
    updated: list[str] = []
    for rel in staged_paths:
        path = ROOT / rel
        if not path.exists():  # staged deletion
            continue
        if _set_last_edited(path):
            updated.append(rel)
    print(f"last_edited is current for {len(staged_paths)} staged document(s)")
    if updated:
        print()
        print("Stage the updated documents, then retry the commit:")
        print(f"  git add -- {' '.join(shlex.quote(path) for path in updated)}")
    return 0


def check_last_edited_staged() -> int:
    """Read-only check that staged documentation carries today's edit date."""
    staged_paths = sorted(
        line
        for line in _git_text(["diff", "--cached", "--name-only"]).splitlines()
        if line.startswith("docs/") and line.endswith(".md")
    )
    stale: list[str] = []
    for rel in staged_paths:
        try:
            text = _git_text(["show", f":{rel}"])
        except RuntimeError:
            continue  # staged deletion
        match = _LAST_EDITED_RE.search(text)
        value = match.group(0).split(":", 1)[1].strip() if match else None
        if value != _today():
            stale.append(rel)

    if not stale:
        print(f"last_edited is current for {len(staged_paths)} staged document(s)")
        return 0

    quoted_paths = " ".join(shlex.quote(path) for path in stale)
    print()
    print("DOCUMENTATION DATES OUT OF DATE — COMMIT STOPPED")
    for path in stale:
        print(f"last_edited must be {_today()}: {path}")
    print()
    print("Run:")
    print("  tools/bin/docsys evidence sync-last-edited")
    print(f"  git add -- {quoted_paths}")
    print("  git commit")
    print()
    print("No files were changed or staged by this check.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docsys evidence")
    subparsers = parser.add_subparsers(dest="command", required=True)

    promote = subparsers.add_parser(
        "promote",
        help="mark explicitly reviewed staged documents verified",
    )
    promote.add_argument("--staged", action="store_true", required=True)
    promote.add_argument(
        "--stage",
        action="store_true",
        help="stage the promoted documentation paths after updating metadata",
    )
    promote.add_argument("paths", nargs="+")

    subparsers.add_parser(
        "check-staged",
        help="validate verified documents against staged evidence",
    )

    subparsers.add_parser(
        "sync-last-edited",
        help="update last_edited in the working tree for staged documentation",
    )
    subparsers.add_parser(
        "check-last-edited",
        help="validate last_edited in staged documentation without writing",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "promote":
            return promote_staged(args.paths, stage=args.stage)
        if args.command == "check-staged":
            return check_staged()
        if args.command == "sync-last-edited":
            return sync_last_edited_staged()
        if args.command == "check-last-edited":
            return check_last_edited_staged()
        raise ValueError(f"unknown evidence command: {args.command}")
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"documentation evidence error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
