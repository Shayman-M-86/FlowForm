---
title: Documentation tools
document_type: implementation
status: scaffold
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-03
related_code: ["generate-reference-docs.py", "validate-doc-links.py", "validate-doc-metadata.py", "docsys/__main__.py", "docsys/research.py"]
change_triggers: ["docsys/"]
related_docs: ["../../docs/project-knowledge/engineering-practices/documentation/documentation-workflow.md", "../../docs/project-knowledge/engineering-practices/documentation/documentation-model.md"]
---

# Documentation tools

Provides lightweight, dependency-free tools for generating and validating the
`docs/` knowledge network and its agent integrations.

## Available tools

`generate-reference-docs.py` regenerates the compact reference output under
`docs/project-knowledge/reference/generated/`.
`validate-doc-links.py` checks that `[[wiki links]]` resolve to Obsidian note
filenames or shortest unique note paths and that relative Markdown links resolve
on disk. `validate-doc-metadata.py` checks required front-matter keys, ISO
`last_edited` dates, title-matching Obsidian aliases, allowed status values,
global title uniqueness, the controlled tag vocabulary, and `related_docs`
resolution.

Use `tools/docs/bin/docsys --help` for documentation discovery, retrieval,
impact review, validation, health checks, and evidence promotion. `find`
returns a small candidate set and `read` loads only the selected outline,
section, or bounded body with exact source line bounds. Exact flags and defaults
live in command help rather than being duplicated here.

`docsys research` launches one fresh, non-persistent local Codex process and
returns a compact cited result. The process uses the existing Codex login,
ignores agent-specific configuration and memories, and runs repository commands
inside a read-only sandbox. Quick research defaults to `gpt-5.6-terra`;
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
