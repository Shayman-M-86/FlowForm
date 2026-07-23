---
title: Documentation scripts
document_type: implementation
status: scaffold
authority: canonical
verified_against_commit: null
related_code: ["generate-repository-tree.py", "validate-doc-links.py", "validate-doc-metadata.py", "docsys/"]
related_docs: ["../../docs/00-overview/documentation-generator-guide.md", "../../docs/00-overview/documentation-model.md"]
---

# Documentation scripts

Provides lightweight, dependency-free scripts for generating and validating the docs/ knowledge network.

## Available scripts

`generate-repository-tree.py` regenerates `docs/90-generated/repository-tree.md`. `validate-doc-links.py` checks that `[[wiki links]]` resolve to Obsidian note filenames or shortest unique note paths and that relative Markdown links resolve on disk. `validate-doc-metadata.py` checks required front-matter keys, title-matching Obsidian aliases, allowed status values, global title uniqueness, the controlled tag vocabulary, and `related_docs` resolution.

The `docsys/` package builds on the same conventions to offer a documentation index, impact detection, freshness checks, deterministic search, task-context assembly, a health dashboard, reviewable update proposals, and an MCP server. See `docsys/README.md`. Run it as `python3 -m docsys <command>` (with `scripts/docs/` on `PYTHONPATH`).

## Conventions enforced

The knowledge-network conventions (titles as identifiers, wiki links, `related_docs`, tags) are defined in `docs/00-overview/documentation-model.md`; the validators are the executable form of those rules.

## Usage expectations

Run scripts from the repository root with `python3`. Both validators exit non-zero when issues are found, so they are safe to wire into CI or hooks.

## Limitations

The validators parse the canonical front-matter shape used across docs/ rather than full YAML, and do not verify that prose claims match the implementation.
