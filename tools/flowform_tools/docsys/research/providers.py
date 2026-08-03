"""Provider selection for the command-line research compatibility entry."""

from __future__ import annotations

import asyncio
from typing import Any

from .codex import run_codex
from .models import ResearchRequest, ResearchRuntimeError


def _run_claude(request: ResearchRequest) -> dict[str, Any]:
    from .session_pool import run_claude_once

    return asyncio.run(run_claude_once(request))


def run_research(request: ResearchRequest) -> dict[str, Any]:
    """Run one local SDK session, with Codex fallback for the auto provider."""
    if request.provider == "codex":
        return run_codex(request)
    try:
        return _run_claude(request)
    except ResearchRuntimeError as claude_error:
        if request.provider == "claude":
            raise
        try:
            result = run_codex(request)
        except ResearchRuntimeError as codex_error:
            raise ResearchRuntimeError(
                f"Claude primary failed ({claude_error}); "
                f"Codex fallback failed ({codex_error})"
            ) from codex_error
        result["runtime"]["fallback_from"] = "claude-agent-sdk"
        result["runtime"]["fallback_reason"] = str(claude_error)[:500]
        return result
