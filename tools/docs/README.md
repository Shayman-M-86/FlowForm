---
title: Documentation tools
document_type: implementation
status: scaffold
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-27
related_code: ["generate-repository-tree.py", "validate-doc-links.py", "validate-doc-metadata.py", "docsys/"]
related_docs: ["../../docs/project-knowledge/engineering-practices/documentation/authoring-guide.md", "../../docs/project-knowledge/engineering-practices/documentation/documentation-model.md"]
---

# Documentation tools

Provides lightweight, dependency-free tools for generating and validating the
`docs/` knowledge network and its agent integrations.

## Available tools

`generate-reference-docs.py` and `generate-repository-tree.py` regenerate
reference output under `docs/project-knowledge/reference/generated/`.
`validate-doc-links.py` checks that `[[wiki links]]` resolve to Obsidian note
filenames or shortest unique note paths and that relative Markdown links resolve
on disk. `validate-doc-metadata.py` checks required front-matter keys, ISO
`last_edited` dates, title-matching Obsidian aliases, allowed status values,
global title uniqueness, the controlled tag vocabulary, and `related_docs`
resolution.

The `docsys/` package builds on the same conventions to offer a documentation index, impact detection, staged evidence verification, freshness checks, deterministic search, task-context assembly, collection-aware validation, advisory documentation-debt analysis, a health dashboard, reviewable update proposals, and an MCP server. See `docsys/README.md`. Run it as `python3 -m docsys <command>` (with `tools/docs/` on `PYTHONPATH`).

`validate-agent-setup.py` validates the dependency-free, shared Codex and
Claude documentation-context skill, their `docs-maintainer` agents, and
matching `flowform-docs` MCP registrations. `hooks/` contains the shared
SessionStart and PostToolUse hook implementations used by both agents; agent
configuration files point here instead of maintaining agent-specific copies.
See `hooks/README.md` for the lifecycle diagram.

## Conventions enforced

The knowledge-network conventions are defined in
`docs/project-knowledge/engineering-practices/documentation/documentation-model.md`;
the validators are the executable form of those rules.

## Usage expectations

Run scripts from the repository root with `python3`. Both validators exit non-zero when issues are found, so they are safe to wire into CI or hooks.

## Limitations

The validators parse the canonical front-matter shape used across docs/ rather than full YAML, and do not verify that prose claims match the implementation.
