---
title: Documentation workflow
aliases: ["Documentation workflow"]
document_type: workflow
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-03
tags: [meta]
related_code:
  - "../../../../AGENTS.md"
  - "../../../../tools/flowform_tools/docsys/commands/research.py"
  - "../../../../tools/flowform_tools/docsys/research/mcp_server.py"
  - "../../../../tools/flowform_tools/docsys/research/session_pool.py"
  - "../../../../tools/flowform_tools/docsys/command_catalog.py"
  - "../../../../tools/flowform_tools/docsys/commands/capabilities.py"
  - "../../../../tools/flowform_tools/docsys/commands/validate.py"
  - "../../../../tools/flowform_tools/docsys/commands/evidence.py"
change_triggers:
  - "../../../../tools/"
  - "../../../../.agents/skills/flowform-doc-context/"
  - "../../../../.agents/skills/flowform-doc-verification/"
related_docs:
  - "Documentation practice"
  - "Documentation model"
---

# Documentation workflow

FlowForm documentation is maintained from repository evidence, at the most
stable level that remains useful. The aim is not to reproduce the codebase in
prose. It is to explain ownership, boundaries, important behaviour, and the
entry point for deeper operational or implementation detail.

## Choose the right level

Project Knowledge should survive routine refactoring. Prefer:

- responsibilities and boundaries over class, resource, or stack inventories;
- lifecycles and ordering constraints over copied commands;
- stable entry points over lists of every script or environment variable;
- links to implementation-local READMEs and command help over duplicated setup;
- generated output over manually maintained catalogues.

Exact procedures belong next to the scripts or configuration they operate.
Plans, alternatives, and unresolved questions belong in the Development
Workspace. If two pages explain the same owner or lifecycle, consolidate them
instead of adding a cross-linked variation.

## Answer-oriented research

Codex and Claude use the same `flowform-doc-context` skill and the same
`tools/bin/docsys` commands. One lightweight MCP server exposes only the
answer-oriented `research` tool; documentation has no lifecycle hook,
platform-specific command, rule, or specialist agent. The canonical skill
lives under `.agents/skills/`; its Claude copy and the root documentation rule
are checked and synchronized by `sync-agent-doc-config.py`.

The MCP server initializes quick and thorough Claude Agent SDK clients during
its lifespan without sending a model prompt. Each research request consumes one
client exactly once, disconnects it, and replaces it with a fresh warm client,
so independent questions do not share context. Claude uses the installed local
account login, not a repository API key. A read-only Bubblewrap boundary,
disabled session persistence, empty inherited MCP configuration, and a bounded
command inventory isolate the research process. Codex is the fresh ephemeral
fallback when the primary provider fails. The compatibility `docsys research`
command follows the same provider order without the MCP server's warm pool.

The command inventory is owned by `docsys capabilities`; the prompt restricts
command selection and the read-only sandbox enforces the worktree boundary. A
result preserves source line bounds and returns a validated evidence packet
instead of its search transcript. The installed Claude Code and Codex clients
retain ownership of account authentication.

Verified current documentation may directly support an explanation-only
answer. For implementation work, draft or scaffold documentation, or a
contradiction, the researcher checks the smallest authoritative code, test,
schema, configuration, CI, or infrastructure surface needed. It reports gaps
and contradictions rather than editing documentation or guessing. The command
validates cited paths and lines against the current worktree. The invoking agent
owns any bounded documentation changes.

## Evidence-first update

For a bounded documentation change:

1. Use focused Docsys discovery only when documentation is explicitly in scope
   or an implementation check reveals a material documentation gap.
2. Find a small candidate set, then read only the selected page or section.
3. Read the current implementation source, test, configuration, automation, or
   infrastructure definition that owns the claim.
4. Write the smallest durable explanation that resolves the reader's question.
5. Remove superseded or duplicated prose and repair navigation in the same
   change.
6. Keep exact existing files in `related_code`; use `change_triggers` only for
   broader review signals.
7. Leave changed Project Knowledge as `draft` with a null evidence digest until
   a reviewer deliberately promotes it.

Do not use historical documentation as proof of current behaviour. A nearby
README is useful orientation, but executable definitions remain authoritative.

## Validation and review

Use `tools/bin/docsys --help` and the relevant command help from the
repository root. Exact flags stay with the executable interface rather than in
Project Knowledge.

When Docsys itself changes, also run its unit tests. Generated pages are
refreshed through their generator rather than edited by hand.

Automation checks structure, metadata, links, collection boundaries, and
evidence drift. Human review still decides whether the prose is accurate,
appropriately general, non-duplicative, and useful without following every
link.

Documentation impact is reviewed once after relevant implementation behaviour
has settled. It is not a task-start requirement and is not repeated for
ordinary follow-up prompts.

Review the changed group for four questions:

- Does each current-state claim have an implementation owner?
- Could routine implementation renaming leave the explanation valid?
- Is exact operational detail maintained in one implementation-local place?
- Can any page disappear because its useful content already has a clear owner?

## Verification

Only Project Knowledge is promoted to `verified`. After semantic review against
the staged implementation evidence, use the shared verification workflow to
calculate and stage the evidence digest. Development Workspace material remains
draft working or historical context.

The pre-commit hook checks document dates and exact-file evidence drift without
rewriting or staging files. A failed check is a review request, not permission
to refresh a digest without reading the page.

## Related documents

- [[documentation-index|Documentation practice]]
- [[documentation-model|Documentation model]]
