"""Prompt construction for Docsys research providers."""

from __future__ import annotations

import json
from pathlib import Path

from ..command_catalog import render_research_cli_policy
from ..core.model import ROOT
from .models import ResearchRequest

_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "research.md"


def build_prompt(request: ResearchRequest) -> str:
    """Build a bounded prompt with an encoded, untrusted request payload."""
    instructions = (
        _PROMPT_PATH.read_text()
        .strip()
        .replace("{{RESEARCH_CLI_TOOLS}}", render_research_cli_policy())
    )
    payload = (
        json.dumps(
            {
                "scope": request.scope or "repository-wide",
                "depth": request.depth,
                "question": request.question,
                "repository_root": str(ROOT),
                "docsys_command": str(ROOT / "tools/bin/docsys"),
            },
            ensure_ascii=False,
            indent=2,
        )
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    return (
        f"{instructions}\n\n"
        "<research_request_json>\n"
        f"{payload}\n"
        "</research_request_json>\n"
    )
