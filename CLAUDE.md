# FlowForm Claude guide

## Project overview

FlowForm is a survey platform for designing and publishing surveys, collecting
responses, and reviewing results.

Its main user-facing areas are:

- **Studio** for authenticated project and survey management.
- **Public Site** for respondents completing published surveys.
- **Backend** for the shared application behaviour and data services.

## Repository map

| Area | Purpose | Local guidance |
| --- | --- | --- |
| `backend/` | Application services and API | `backend/CLAUDE.md` |
| `frontend/` | Studio, Public Site, and shared interface packages | `frontend/CLAUDE.md` |
| `infra/` | Environments, deployment, runtime, and supporting resources | Follow nearby documentation and scripts |
| `scripts/` | Repository-wide development and maintenance automation | Read each entry point before running it |
| `docs/` | Current Project Knowledge and Development Workspace | Start with `docs/docs-index.md` |
| `tools/` | Development integrations and supporting utilities | Keep changes within the tool's boundary |

More specific `CLAUDE.md` files override this guide within their directories.

## Working principles

- Treat the implementation, tests, configuration, and automation as the source
  of truth.
- Keep changes within the requested area and preserve unrelated work.
- Understand the owning area before editing across boundaries.
- Validate changes in proportion to their impact and report uncertainty
  honestly.
- Keep proposals and unfinished work separate from descriptions of current
  behaviour.

## Documentation

Documentation is optional context, not a task-start requirement. Use the
`flowform-doc-context` skill for explicit documentation work, answer-oriented
research into established FlowForm behaviour, or after finding a material
documentation gap. Call the isolated `flowform-research` MCP tool for compact
factual briefings and delegate bounded documentation edits to `docs-maintainer`.
The research service starts a fresh local Codex process and returns
source-backed evidence without editing.
Verified current documents may directly answer explanation-only questions;
inspect implementation when implementing, diagnosing, explicitly verifying, or
resolving a material gap or contradiction.

After behavioural or architectural changes, review the impacted documentation.
Update only pages whose meaning changed, and regenerate generated documentation
instead of editing it manually. After reviewing implementation-backed claims,
use `docsys evidence promote --staged` to record staged evidence for Project
Knowledge; Development Workspace is not verified. The pre-commit hook enforces
verification drift and checks document `last_edited` dates without modifying
or staging files. Treat
`old-docs/` as historical material.

Codex and Claude share `flowform-research` for isolated factual research and
provide `docs-maintainer` for bounded documentation work. The parent agent
remains responsible for integration and final validation. Use the shared
`flowform-doc-verification` skill when the user wants to select, review,
approve, and promote specific Project Knowledge pages.

## Handoff

Summarize what changed, what was validated, and any remaining gaps or
assumptions. Do not commit or push unless the user explicitly requests it.
