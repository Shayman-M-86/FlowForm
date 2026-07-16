#!/usr/bin/env python3
"""Shared helpers for the FlowForm Docsys documentation-impact hooks.

These helpers glue Claude Code's hook lifecycle to the existing ``docsys``
tooling. They do NOT reimplement impact detection, git diffing, or the document
model — that logic lives in ``scripts/docs/docsys/`` and is imported here.

State model
-----------
Per-session state lives in ``.docsys/hook-state/<session_id>.json`` (gitignored)
and records:

- ``base_commit``   the repository HEAD captured at task start (SessionStart)
- ``reviewed``      a review record written by the agent, keyed by a fingerprint
                    of the changed implementation files, so a completed review
                    unblocks the next Stop attempt and does not loop

The fingerprint ties a review to a specific set of changed files: if the agent
keeps editing after reviewing, the fingerprint changes and a fresh review is
requested; if nothing new changed, the recorded review stands.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Repo root: .claude/hooks/docsys_hook_lib.py -> parents[2].
ROOT = Path(__file__).resolve().parents[2]
DOCSYS_PATH = ROOT / "scripts" / "docs"
STATE_DIR = ROOT / ".docsys" / "hook-state"

# Implementation surfaces whose changes can plausibly affect canonical docs.
# Kept deliberately broad but excludes docs, generated output, and pure noise.
_IMPL_PREFIXES = (
    "backend/",
    "frontend/",
    "infra/",
    "scripts/",
    "tools/",
)
_IGNORE_SUFFIXES = (
    ".md",
    ".lock",
    ".snap",
)
_IGNORE_SUBSTRINGS = (
    "/node_modules/",
    "/__pycache__/",
    "/.venv/",
    "/dist/",
    "/coverage/",
)


def _run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    )
    return proc.returncode, proc.stdout


def read_hook_input() -> dict:
    """Read hook input from whichever channel the calling agent uses.

    Claude Code passes a JSON object on stdin. Codex (per this repo's existing
    hooks) exposes the payload via the ``CLAUDE_TOOL_INPUT`` environment
    variable and may leave stdin empty. This adapter accepts either, so the
    same hook scripts work for both agents.
    """
    # Prefer stdin JSON (Claude Code, and any agent that supplies it).
    raw = ""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
    except (OSError, ValueError):
        raw = ""
    if raw.strip():
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass

    # Fall back to the env-var payload used by Codex hooks in this repo.
    for var in ("CLAUDE_TOOL_INPUT", "CODEX_HOOK_INPUT", "CODEX_TOOL_INPUT"):
        env_raw = os.environ.get(var)
        if env_raw:
            try:
                data = json.loads(env_raw)
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, ValueError):
                continue
    return {}


def resolve_session_id(data: dict) -> str:
    """Return a stable session id, tolerating agents that omit one.

    Claude Code always supplies ``session_id``. If an agent does not, fall back
    to an agent-provided id, else a per-working-copy constant so state is still
    scoped to this checkout (a single active task at a time).
    """
    for key in ("session_id", "sessionId", "session", "conversation_id"):
        val = data.get(key)
        if val:
            return str(val)
    for var in ("CODEX_SESSION_ID", "CLAUDE_SESSION_ID"):
        val = os.environ.get(var)
        if val:
            return val
    # Deterministic per-checkout fallback: one implicit session per repo path.
    return "local-" + re.sub(r"[^A-Za-z0-9]", "", str(ROOT))[-16:]


def current_head() -> str | None:
    code, out = _run(["rev-parse", "HEAD"])
    return out.strip() if code == 0 else None


def state_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "unknown")
    return STATE_DIR / f"{safe}.json"


def load_state(session_id: str) -> dict:
    path = state_path(session_id)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(session_id: str, state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path(session_id).write_text(json.dumps(state, indent=2) + "\n")


def is_impl_file(path: str) -> bool:
    """True when a changed path is an implementation surface, not docs/noise."""
    if path.startswith("docs/") or path.startswith("old-docs/"):
        return False
    if any(sub in path for sub in _IGNORE_SUBSTRINGS):
        return False
    if path.endswith(_IGNORE_SUFFIXES):
        return False
    return path.startswith(_IMPL_PREFIXES)


def changed_files_since(base: str | None) -> tuple[list[str], list[str]]:
    """Return (implementation_files, doc_files) changed since ``base``.

    Compares committed history since ``base`` plus the current working tree
    (tracked changes and untracked files), so changes made during the task are
    captured whether or not they were committed.
    """
    files: set[str] = set()

    if base:
        code, out = _run(["diff", "--name-only", base, "HEAD"])
        if code == 0:
            files.update(x for x in out.splitlines() if x.strip())
    # Working tree vs HEAD (staged + unstaged).
    _, tracked = _run(["diff", "--name-only", "HEAD"])
    files.update(x for x in tracked.splitlines() if x.strip())
    # Untracked, respecting .gitignore.
    _, untracked = _run(["ls-files", "--others", "--exclude-standard"])
    files.update(x for x in untracked.splitlines() if x.strip())

    impl = sorted(f for f in files if is_impl_file(f))
    docs = sorted(f for f in files if f.startswith("docs/"))
    return impl, docs


def fingerprint(files: list[str]) -> str:
    """Stable fingerprint of a set of changed implementation files."""
    joined = "\n".join(sorted(files))
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


# Cap on how many documents the review gate names. A gate that lists 15 docs
# reads as noise and gets ignored; a short, specific list gets reviewed.
MAX_IMPACTED = 8


def _specificity(item) -> int:
    """Rank a match by how precisely it targets the document (higher = better).

    An exact-file match is a far stronger signal that a specific document is
    affected than a broad top-level directory pattern (e.g. ``backend/app/``),
    which matches almost any backend change. We surface the specific matches
    first so the review gate stays focused.
    """
    kinds = {m.kind for m in item.matches}
    if "exact" in kinds:
        return 3
    if "glob" in kinds:
        return 2
    # Directory match: reward deeper (more specific) directories.
    depth = max((p.count("/") for p in {m.pattern for m in item.matches}), default=0)
    return min(1, depth // 3)  # very shallow dirs score 0, deeper score 1


def detect_impacted_docs(impl_files: list[str]) -> list[dict]:
    """Reuse docsys impact detection; return high-confidence canonical docs.

    Imports the existing ``docsys`` package rather than duplicating any logic.
    Returns a focused, capped list of ``{title, path, confidence}`` for
    canonical documents, most specifically-matched first. Only high-confidence
    (exact-file) matches are returned, so a broad directory edit no longer names
    the whole architecture section. Generated documents are excluded (they are
    reproduced by their generators, not hand-reviewed).
    """
    if str(DOCSYS_PATH) not in sys.path:
        sys.path.insert(0, str(DOCSYS_PATH))
    try:
        # docsys lives under scripts/docs, added to sys.path above at runtime;
        # static analysers cannot see it, hence the ignores.
        from docsys.impact import detect_impact  # type: ignore[import-not-found]  # noqa: E402
        from docsys.model import DocSet  # type: ignore[import-not-found]  # noqa: E402
    except Exception:
        # If docsys is unavailable, never block completion.
        return []

    docset = DocSet.load()
    impacted = detect_impact(impl_files, docset)
    candidates = [
        item
        for item in impacted
        if item.confidence == "high"
        and item.doc.authority == "canonical"
        and not item.doc.is_generated
    ]
    # Prefer specific matches and higher confidence; keep it short.
    conf_rank = {"high": 0, "medium": 1}
    candidates.sort(
        key=lambda i: (-_specificity(i), conf_rank[i.confidence], i.doc.rel_path)
    )
    return [
        {
            "title": item.doc.title,
            "path": item.doc.rel_path,
            "confidence": item.confidence,
        }
        for item in candidates[:MAX_IMPACTED]
    ]
