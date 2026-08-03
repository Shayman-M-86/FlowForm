"""Bounded, read-only repository retrieval for documentation research."""

from __future__ import annotations

import fnmatch
import subprocess
from functools import lru_cache
from pathlib import Path, PurePosixPath

from .model import ROOT

MAX_SEARCH_RESULTS = 20
MAX_READ_LINES = 200
MAX_READ_CHARS = 12_000

_ALLOWED_NAMES = {"Caddyfile", "Dockerfile", "Makefile"}
_ALLOWED_SUFFIXES = {
    ".astro",
    ".cfg",
    ".css",
    ".graphql",
    ".hcl",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".sql",
    ".tf",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
_DENIED_PARTS = {
    ".agents",
    ".cache",
    ".claude",
    ".codex",
    ".docsys",
    ".git",
    ".idea",
    ".venv",
    ".vscode",
    "__pycache__",
    "dist",
    "node_modules",
    "old-docs",
}
_DENIED_NAMES = {
    ".env",
    ".env.local",
    "agents.md",
    "auth.json",
    "claude.md",
    "credentials.json",
    "token.json",
}
_DENIED_SUFFIXES = {".key", ".p12", ".pem", ".pfx"}


def _normalise_repo_path(value: str, *, label: str) -> str:
    raw = value.strip().replace("\\", "/").rstrip("/")
    if not raw:
        raise ValueError(f"{label} must not be empty")
    path = PurePosixPath(raw)
    if raw.startswith("/") or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{label} must be a normalized repository-relative path")
    return path.as_posix()


def _is_safe_path(rel_path: str) -> bool:
    path = PurePosixPath(rel_path)
    lowered_parts = {part.casefold() for part in path.parts}
    if lowered_parts.intersection(_DENIED_PARTS):
        return False
    name = path.name.casefold()
    if name in _DENIED_NAMES or name.startswith(".env."):
        return False
    if path.suffix.casefold() in _DENIED_SUFFIXES:
        return False
    return path.name in _ALLOWED_NAMES or path.suffix.casefold() in _ALLOWED_SUFFIXES


@lru_cache(maxsize=1)
def repository_files() -> tuple[str, ...]:
    """Return tracked and visible untracked text files, excluding ignored files."""
    completed = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths = completed.stdout.decode(errors="replace").split("\0")
    return tuple(sorted(path for path in paths if path and _is_safe_path(path)))


def _resolve_readable(path_value: str) -> tuple[str, Path]:
    rel_path = _normalise_repo_path(path_value, label="path")
    if rel_path not in repository_files():
        raise ValueError("path is not an allowed repository source file")
    path = ROOT.joinpath(*PurePosixPath(rel_path).parts)
    if path.is_symlink() or not path.is_file():
        raise ValueError("path is not a readable regular file")
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("path must stay inside the repository") from exc
    return rel_path, path


def search_source(
    query: str,
    *,
    scope: str | None = None,
    file_pattern: str | None = None,
    limit: int = 10,
) -> dict:
    """Search bounded source lines using a literal, case-insensitive query."""
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    if len(query) > 200:
        raise ValueError("query must contain at most 200 characters")
    if not 1 <= limit <= MAX_SEARCH_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_SEARCH_RESULTS}")
    scope_value = (
        _normalise_repo_path(scope, label="scope") if scope is not None else None
    )
    if file_pattern is not None:
        file_pattern = file_pattern.strip()
        if not file_pattern or "/" in file_pattern or "\\" in file_pattern:
            raise ValueError("file_pattern must be one filename glob")

    needle = query.casefold()
    matches: list[dict[str, object]] = []
    total = 0
    for rel_path in repository_files():
        if scope_value and not (
            rel_path == scope_value or rel_path.startswith(scope_value + "/")
        ):
            continue
        if file_pattern and not fnmatch.fnmatch(
            PurePosixPath(rel_path).name, file_pattern
        ):
            continue
        path = ROOT.joinpath(*PurePosixPath(rel_path).parts)
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if needle not in line.casefold():
                continue
            total += 1
            if len(matches) < limit:
                text = line.strip()
                matches.append(
                    {
                        "path": rel_path,
                        "line": line_number,
                        "text": text[:300] + ("…" if len(text) > 300 else ""),
                    }
                )
    return {
        "items": matches,
        "total": total,
        "returned": len(matches),
        "truncated": total > len(matches),
    }


def read_source(path: str, *, start_line: int, end_line: int) -> dict:
    """Read one exact, bounded source range with one-based line coordinates."""
    if start_line < 1 or end_line < start_line:
        raise ValueError("line range must be positive and ordered")
    if end_line - start_line + 1 > MAX_READ_LINES:
        raise ValueError(f"read_source returns at most {MAX_READ_LINES} lines")
    rel_path, resolved = _resolve_readable(path)
    lines = resolved.read_text(errors="replace").splitlines()
    if start_line > max(1, len(lines)):
        raise ValueError("start_line is beyond the end of the file")
    actual_end = min(end_line, len(lines))
    content = "\n".join(lines[start_line - 1 : actual_end])
    truncated = len(content) > MAX_READ_CHARS
    if truncated:
        content = content[: MAX_READ_CHARS - 1].rstrip() + "…"
    return {
        "path": rel_path,
        "start_line": start_line,
        "end_line": actual_end,
        "content": content,
        "truncated": truncated,
    }
