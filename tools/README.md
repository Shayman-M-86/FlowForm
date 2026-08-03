---
title: Documentation tools
document_type: implementation
status: scaffold
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-03
related_code: ["bin/docsys", "bin/flowform-doc-research", "flowform_tools/docsys/__main__.py", "flowform_tools/docsys/command_catalog.py", "flowform_tools/docsys/core/model.py", "flowform_tools/docsys/commands/validate.py", "flowform_tools/docsys/commands/research.py", "flowform_tools/docsys/research/mcp_server.py", "flowform_tools/docsys/research/session_pool.py"]
change_triggers: ["docsys/"]
related_docs: ["../../docs/project-knowledge/engineering-practices/documentation/documentation-workflow.md", "../../docs/project-knowledge/engineering-practices/documentation/documentation-model.md"]
---

# Documentation tools

Provides lightweight tools for generating and validating the `docs/` knowledge
network and its agent integrations. Commit/CI validation stays dependency-free;
discovery uses the optional `docs` dependencies and research uses the separate
`research` extra.

## Available tools

`docsys generate-reference` regenerates compact reference output.
`docsys validate-links` checks wiki and relative Markdown links. `docsys
validate` owns front-matter, collection, and link validation.

Use `tools/bin/docsys --help` for documentation discovery, retrieval,
impact review, validation, health checks, and evidence promotion. `find`
returns a small candidate set and `read` loads only the selected outline,
section, or bounded body with exact source line bounds. Exact flags and defaults
live in command help rather than being duplicated here.

`docsys capabilities --format json` is the canonical machine-readable inventory
of Docsys command effects, the research MCP runtime, and its read-only tools.

`flowform-doc-research` exposes one MCP tool. At server startup it uses the
Claude Agent SDK to initialize a quick Sonnet session and a thorough Opus
session without sending a model prompt. Each tool call consumes one session,
disconnects it, and replaces it with a fresh warm session. Claude runs through
the installed CLI's local account login in a read-only Bubblewrap boundary;
provider API-key and cloud credential variables are removed. Codex remains an
ephemeral, local-login fallback. `docsys research` is the non-warm compatibility
entry point and follows the same provider policy.

This is developer-local automation for the repository. It must not be exposed
as a shared or multi-user service backed by personal subscription credentials.

`validate-agent-setup.py` checks the shared documentation skills,
root documentation rules, the single-tool research MCP, absence of lifecycle
hooks, and isolated research-process flags. `sync-agent-doc-config.py` keeps Claude's
skill mirrors and root documentation section aligned with the canonical copies.

## Conventions enforced

The knowledge-network conventions are defined in
`docs/project-knowledge/engineering-practices/documentation/documentation-model.md`;
the validators are the executable form of those rules.

## Usage expectations

Run scripts from the repository root. Use each command's `--help` before
requesting broad output. Validators exit non-zero when issues are found.

## Limitations

The validators parse the canonical front-matter shape used across docs/ rather than full YAML, and do not verify that prose claims match the implementation.
