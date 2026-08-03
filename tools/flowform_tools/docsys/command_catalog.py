"""Canonical Docsys commands and spawned-research CLI policy."""

from __future__ import annotations

DOCSYS_COMMANDS = {
    "find": {
        "module": "flowform_tools.docsys.commands.query",
        "description": "find a small set of relevant documents",
        "access": "read-only",
    },
    "read": {
        "module": "flowform_tools.docsys.commands.retrieve",
        "description": "read one exact document or section",
        "access": "read-only",
    },
    "research": {
        "module": "flowform_tools.docsys.commands.research",
        "description": "answer one question in a fresh Codex session",
        "access": "read-only-worktree",
    },
    "impact": {
        "module": "flowform_tools.docsys.commands.impact",
        "description": "find documentation affected by code changes",
        "access": "read-only",
    },
    "freshness": {
        "module": "flowform_tools.docsys.commands.freshness",
        "description": "check implementation evidence freshness",
        "access": "read-only",
    },
    "health": {
        "module": "flowform_tools.docsys.commands.health",
        "description": "summarize documentation health",
        "access": "conditional-write",
        "write_controls": ["--write"],
    },
    "debt": {
        "module": "flowform_tools.docsys.commands.debt",
        "description": "inspect documentation maintenance debt",
        "access": "read-only",
    },
    "validate": {
        "module": "flowform_tools.docsys.commands.validate",
        "description": "validate documentation structure",
        "access": "read-only",
    },
    "index": {
        "module": "flowform_tools.docsys.commands.index",
        "description": "regenerate the documentation index",
        "access": "writes-worktree",
    },
    "evidence": {
        "module": "flowform_tools.docsys.commands.evidence",
        "description": "check or promote verification evidence",
        "access": "conditional-write-and-stage",
        "write_controls": ["promote", "sync-last-edited"],
    },
    "capabilities": {
        "module": "flowform_tools.docsys.commands.capabilities",
        "description": "list Docsys commands and research CLI tools",
        "access": "read-only",
    },
    "validate-agent-setup": {
        "module": "flowform_tools.docsys.maintenance.validate_agent_setup",
        "description": "validate the shared agent documentation workflow",
        "access": "read-only",
    },
    "validate-links": {
        "module": "flowform_tools.docsys.maintenance.validate_doc_links",
        "description": "validate wiki links and relative Markdown links",
        "access": "read-only",
    },
    "generate-reference": {
        "module": "flowform_tools.docsys.maintenance.generate_reference_docs",
        "description": "regenerate the compact reference documentation",
        "access": "writes-worktree",
    },
    "sync-agent-config": {
        "module": "flowform_tools.docsys.maintenance.sync_agent_doc_config",
        "description": "mirror shared doc skills into agent configuration",
        "access": "writes-worktree",
    },
}

RESEARCH_CLI_TOOLS = (
    {
        "executable": "tools/bin/docsys",
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
