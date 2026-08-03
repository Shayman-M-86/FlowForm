"""Canonical Docsys commands and spawned-research CLI policy."""

from __future__ import annotations

DOCSYS_COMMANDS = {
    "find": {
        "module": "docsys.query",
        "description": "find a small set of relevant documents",
        "access": "read-only",
    },
    "read": {
        "module": "docsys.retrieve",
        "description": "read one exact document or section",
        "access": "read-only",
    },
    "research": {
        "module": "docsys.research",
        "description": "answer one question in a fresh Codex session",
        "access": "read-only-worktree",
    },
    "impact": {
        "module": "docsys.impact",
        "description": "find documentation affected by code changes",
        "access": "read-only",
    },
    "freshness": {
        "module": "docsys.freshness",
        "description": "check implementation evidence freshness",
        "access": "read-only",
    },
    "health": {
        "module": "docsys.health",
        "description": "summarize documentation health",
        "access": "conditional-write",
        "write_controls": ["--write"],
    },
    "debt": {
        "module": "docsys.debt",
        "description": "inspect documentation maintenance debt",
        "access": "read-only",
    },
    "validate": {
        "module": "docsys.validate",
        "description": "validate documentation structure",
        "access": "read-only",
    },
    "index": {
        "module": "docsys.index",
        "description": "regenerate the documentation index",
        "access": "writes-worktree",
    },
    "evidence": {
        "module": "docsys.evidence",
        "description": "check or promote verification evidence",
        "access": "conditional-write-and-stage",
        "write_controls": ["promote", "sync-last-edited"],
    },
    "capabilities": {
        "module": "docsys.capabilities",
        "description": "list Docsys commands and research CLI tools",
        "access": "read-only",
    },
}

RESEARCH_CLI_TOOLS = (
    {
        "executable": "tools/docs/bin/docsys",
        "usage": "find and read bounded FlowForm documentation",
        "allowed_subcommands": ["find", "read"],
    },
    {"executable": "rg", "usage": "bounded literal or regex content search"},
    {"executable": "fd", "usage": "bounded file and directory discovery"},
    {"executable": "ast-grep", "usage": "syntax-aware source search"},
    {"executable": "jq", "usage": "query one exact JSON file"},
    {"executable": "yq", "usage": "query one exact structured config file"},
    {"executable": "sed", "usage": "read one exact text range"},
    {"executable": "nl", "usage": "add stable line numbers to a text range"},
)


def render_research_cli_policy() -> str:
    """Render the compact command list embedded in the research prompt."""
    return "\n".join(
        f"- `{tool['executable']}`: {tool['usage']}" for tool in RESEARCH_CLI_TOOLS
    )
