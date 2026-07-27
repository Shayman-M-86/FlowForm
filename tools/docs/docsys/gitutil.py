#!/usr/bin/env python3
"""Thin, defensive wrappers over ``git`` for the documentation tools.

Everything here degrades gracefully: if the repository is shallow, a commit is
missing, or ``git`` is unavailable, callers get an empty result and a reason
rather than a traceback. Freshness and impact tooling must run in CI and on
developer machines with equal predictability.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass

from .model import ROOT


def _run(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def is_git_repo() -> bool:
    code, _, _ = _run(["rev-parse", "--git-dir"])
    return code == 0


def current_commit() -> str | None:
    code, out, _ = _run(["rev-parse", "HEAD"])
    return out.strip() if code == 0 else None


def commit_exists(commit: str) -> bool:
    if not commit:
        return False
    code, _, _ = _run(["cat-file", "-e", f"{commit}^{{commit}}"])
    return code == 0


def short(commit: str | None) -> str:
    return (commit or "")[:12]


@dataclass
class DiffResult:
    """Files that changed between two states, plus how the diff was derived."""

    files: list[str]
    base: str | None
    head: str | None
    reason: str  # human-readable description of what was compared


def _parse_name_status(out: str) -> list[str]:
    files = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        # Renames/copies report old and new path; keep the new one.
        path = parts[-1]
        if status.startswith("D"):
            # Deletions still matter to impact analysis; keep them.
            files.append(path)
        else:
            files.append(path)
    return files


def changed_files(base: str | None = None, head: str | None = None) -> DiffResult:
    """Return files changed between ``base`` and ``head``.

    With no arguments, reports the working-tree changes (staged, unstaged, and
    untracked) against ``HEAD`` — the common local case. With a ``base`` it
    diffs ``base...head`` (merge-base three-dot), matching how CI compares a
    branch against its target.
    """
    if not is_git_repo():
        return DiffResult([], base, head, "not a git repository")

    if base:
        head = head or "HEAD"
        if not commit_exists(base):
            return DiffResult([], base, head, f"base commit {short(base)} not found")
        code, out, err = _run(["diff", "--name-status", f"{base}...{head}"])
        if code != 0:
            # Fall back to a two-dot diff when no merge base exists.
            code, out, err = _run(["diff", "--name-status", base, head])
        if code != 0:
            return DiffResult([], base, head, f"git diff failed: {err.strip()}")
        return DiffResult(
            _parse_name_status(out), base, head, f"{short(base)}...{short(head)}"
        )

    # Working-tree mode: tracked changes vs HEAD plus untracked files.
    head = current_commit()
    _, tracked, _ = _run(["diff", "--name-status", "HEAD"])
    _, untracked, _ = _run(["ls-files", "--others", "--exclude-standard"])
    files = _parse_name_status(tracked)
    files += [line for line in untracked.splitlines() if line.strip()]
    # De-duplicate while preserving order.
    seen: dict[str, None] = {}
    for f in files:
        seen.setdefault(f, None)
    return DiffResult(list(seen), head, None, "working tree vs HEAD")


def files_changed_since(commit: str) -> DiffResult:
    """Files changed between ``commit`` and the current ``HEAD`` (committed).

    Used by freshness: it answers "what has moved in the codebase since a
    document was last verified?" against committed history only.
    """
    if not is_git_repo():
        return DiffResult([], commit, None, "not a git repository")
    if not commit or not commit_exists(commit):
        return DiffResult([], commit, None, f"commit {short(commit)} not found")
    head = current_commit()
    code, out, err = _run(["diff", "--name-status", commit, "HEAD"])
    if code != 0:
        return DiffResult([], commit, head, f"git diff failed: {err.strip()}")
    return DiffResult(
        _parse_name_status(out), commit, head, f"{short(commit)}..{short(head)}"
    )


def commit_distance(commit: str) -> int | None:
    """Number of commits between ``commit`` and ``HEAD`` (``None`` if unknown)."""
    if not commit_exists(commit):
        return None
    code, out, _ = _run(["rev-list", "--count", f"{commit}..HEAD"])
    if code != 0:
        return None
    try:
        return int(out.strip())
    except ValueError:
        return None
