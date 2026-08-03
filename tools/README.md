---
title: Documentation tools
document_type: implementation
status: scaffold
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-03
related_code: ["bin/docsys", "flowform_tools/docsys/__main__.py", "flowform_tools/docsys/command_catalog.py", "flowform_tools/docsys/core/model.py", "flowform_tools/docsys/commands/validate.py", "flowform_tools/docsys/commands/research.py"]
change_triggers: ["docsys/"]
related_docs: ["../../docs/project-knowledge/engineering-practices/documentation/documentation-workflow.md", "../../docs/project-knowledge/engineering-practices/documentation/documentation-model.md"]
---

# Documentation tools

Provides lightweight tools for generating and validating the `docs/` knowledge
network and its agent integrations. Commit/CI validation stays dependency-free;
discovery and research use the optional `docs` dependencies.

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
of Docsys command effects and the CLI tools exposed to a spawned researcher.

`docsys research` launches one fresh, non-persistent local Codex process and
returns a compact cited result. The process uses the existing Codex login,
starts outside the repository so project configuration is not discovered,
ignores agent-specific configuration and memories, and reads the repository
through a prompt-bounded command set inside a read-only sandbox. Quick research
defaults to `gpt-5.6-terra`;
thorough research defaults to `gpt-5.6-sol`. Either model may be overridden.

`validate-agent-setup.py` checks the shared documentation skills,
root documentation rules, absence of documentation MCP and lifecycle hooks,
and isolated research-process flags. `sync-agent-doc-config.py` keeps Claude's
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
