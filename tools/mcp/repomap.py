"""FlowForm repomap MCP server.

Orchestrates an iterative repo-summarisation workflow:

1. Claude calls get_next_path() to receive the next path to summarise.
2. Claude reads that path and calls save_summary(path, summary).
3. Repeat until get_next_path() returns {"done": true}.
4. Claude calls build_map() to write one rule file per path into
   .claude/rules/repomap/, each with a paths: frontmatter so it loads
   only when Claude works within that directory.

Shortcut: call import_from_repomap_md() to parse an existing repomap.md
and split it into rule files immediately, skipping the summarisation loop.

The include list is read from .claude/repomap-config.json at the repo root:

    {
      "output_dir": ".claude/rules/repomap",
      "import_source": ".claude/repomap.md",
      "paths": [
        "backend/app/services/",
        "frontend/apps/studio-app/src/api/",
        ...
      ]
    }

Run:

    bash tools/mcp/repomap_run.sh
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CONFIG_PATH = REPO_ROOT / ".claude" / "repomap-config.json"

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

_queue: list[str] = []
_queue_index: int = 0
_summaries: dict[str, str] = {}
_output_dir: Path = REPO_ROOT / ".claude" / "rules" / "repomap"
_import_source: Path = REPO_ROOT / ".claude" / "repomap.md"
_session_active: bool = False


def _load_config() -> tuple[list[str], Path, Path]:
    if not CONFIG_PATH.exists():
        return [], REPO_ROOT / ".claude" / "rules" / "repomap", REPO_ROOT / ".claude" / "repomap.md"
    with CONFIG_PATH.open() as f:
        data = json.load(f)
    paths = data.get("paths", [])
    out = REPO_ROOT / data.get("output_dir", ".claude/rules/repomap")
    src = REPO_ROOT / data.get("import_source", ".claude/repomap.md")
    return paths, out, src


def _reset_session() -> None:
    global _queue, _queue_index, _summaries, _output_dir, _import_source, _session_active
    _queue, _output_dir, _import_source = _load_config()
    _queue_index = 0
    _summaries = {}
    _session_active = True


def _path_to_filename(path: str) -> str:
    """Convert a directory path to a safe rule filename."""
    slug = path.strip("/").replace("/", "-")
    slug = re.sub(r"[^a-zA-Z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return f"{slug}.md"


def _path_to_glob(path: str) -> str:
    """Derive the paths: glob — just append ** to the directory path."""
    return path.rstrip("/") + "/**"


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(name="flowform-repomap")


@mcp.tool()
def start_session() -> dict:
    """Start a new repomap session.

    Loads the include list from .claude/repomap-config.json and resets state.
    Call this first before get_next_path().
    Returns the full list of paths that will be summarised.
    """
    _reset_session()
    return {
        "paths": _queue,
        "total": len(_queue),
        "output_dir": str(_output_dir),
        "message": f"Session started. {len(_queue)} paths to summarise.",
    }


@mcp.tool()
def get_next_path() -> dict:
    """Return the next path to summarise.

    Returns {"done": true} when all paths have been processed.
    Each path is a relative path from the repo root.
    Read the directory listing or file contents at that path, write a
    concise summary (2-4 sentences), then call save_summary().
    """
    global _queue_index

    if not _session_active:
        return {"error": "No active session. Call start_session() first."}

    if _queue_index >= len(_queue):
        return {"done": True, "message": "All paths processed. Call build_map() now."}

    path = _queue[_queue_index]
    _queue_index += 1
    full_path = REPO_ROOT / path
    exists = full_path.exists()
    is_dir = full_path.is_dir() if exists else False

    return {
        "done": False,
        "path": path,
        "full_path": str(full_path),
        "type": "directory" if is_dir else "file",
        "exists": exists,
        "remaining": len(_queue) - _queue_index,
    }


@mcp.tool()
def save_summary(path: str, summary: str) -> dict:
    """Save a summary for a path.

    Call this after reading each path returned by get_next_path().
    summary should be 2-4 sentences describing what lives in that
    folder or file — purpose, key contents, and any notable patterns.
    """
    if not _session_active:
        return {"error": "No active session. Call start_session() first."}

    _summaries[path] = summary.strip()
    return {
        "saved": path,
        "total_saved": len(_summaries),
        "remaining": len(_queue) - _queue_index,
    }


@mcp.tool()
def build_map() -> dict:
    """Write one rule file per summarised path into .claude/rules/repomap/.

    Each file has a paths: frontmatter derived from the directory path,
    so it loads only when Claude works within that area.

    Call this after all paths have been processed (get_next_path returned done=true).
    Returns the list of files written.
    """
    if not _session_active:
        return {"error": "No active session. Call start_session() first."}

    if not _summaries:
        return {"error": "No summaries saved yet. Run the full summarisation loop first."}

    _output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    written: list[str] = []

    for path in _queue:
        summary = _summaries.get(path)
        if summary is None:
            continue

        glob = _path_to_glob(path)
        filename = _path_to_filename(path)
        file_path = _output_dir / filename

        content = "\n".join([
            "---",
            f"paths: {glob}",
            "---",
            "",
            f"# {path}",
            "",
            f"_Last updated: {now} by /repomap_",
            "",
            summary,
            "",
        ])

        file_path.write_text(content, encoding="utf-8")
        written.append(str(file_path.relative_to(REPO_ROOT)))

    return {
        "files_written": written,
        "total": len(written),
        "output_dir": str(_output_dir.relative_to(REPO_ROOT)),
    }


@mcp.tool()
def import_from_repomap_md(source: str | None = None) -> dict:
    """Parse an existing repomap.md and write rule files immediately.

    Skips the full summarisation loop — useful after a server restart when
    repomap.md already exists and you just want to split it into rule files.

    source: optional path relative to repo root. Defaults to import_source
    from repomap-config.json (typically .claude/repomap.md).
    """
    _, out_dir, default_src = _load_config()
    src_path = REPO_ROOT / source if source else default_src

    if not src_path.exists():
        return {"error": f"Source file not found: {src_path.relative_to(REPO_ROOT)}"}

    text = src_path.read_text(encoding="utf-8")

    # Parse ## `path` sections
    parsed: dict[str, str] = {}
    current_path: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        header_match = re.match(r"^## `(.+?)`\s*$", line)
        if header_match:
            if current_path is not None:
                parsed[current_path] = "\n".join(current_lines).strip()
            current_path = header_match.group(1)
            current_lines = []
        elif current_path is not None:
            # Skip the _Last updated_ line
            if not re.match(r"^_Last updated:", line):
                current_lines.append(line)

    if current_path is not None:
        parsed[current_path] = "\n".join(current_lines).strip()

    if not parsed:
        return {"error": "No sections found in source file. Expected ## `path/` headings."}

    out_dir.mkdir(parents=True, exist_ok=True)
    now = src_path.stat().st_mtime
    date_str = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")
    written: list[str] = []

    for path, summary in parsed.items():
        if not summary:
            continue
        glob = _path_to_glob(path)
        filename = _path_to_filename(path)
        file_path = out_dir / filename
        content = "\n".join([
            "---",
            f"paths: {glob}",
            "---",
            "",
            f"# {path}",
            "",
            f"_Last updated: {date_str} by /repomap_",
            "",
            summary,
            "",
        ])
        file_path.write_text(content, encoding="utf-8")
        written.append(str(file_path.relative_to(REPO_ROOT)))

    return {
        "files_written": written,
        "total": len(written),
        "output_dir": str(out_dir.relative_to(REPO_ROOT)),
        "source": str(src_path.relative_to(REPO_ROOT)),
    }


@mcp.tool()
def get_session_status() -> dict:
    """Return current session progress."""
    return {
        "active": _session_active,
        "total_paths": len(_queue),
        "processed": _queue_index,
        "summaries_saved": len(_summaries),
        "remaining": max(0, len(_queue) - _queue_index),
        "saved_paths": list(_summaries.keys()),
    }


if __name__ == "__main__":
    mcp.run()
