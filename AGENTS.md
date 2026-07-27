# FlowForm agent guide

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
| `backend/` | Application services and API | `backend/AGENTS.md` |
| `frontend/` | Studio, Public Site, and shared interface packages | `frontend/AGENTS.md` |
| `infra/` | Environments, deployment, runtime, and supporting resources | Follow nearby documentation and scripts |
| `scripts/` | Repository-wide development and maintenance automation | Read each entry point before running it |
| `docs/` | Current Project Knowledge and Development Workspace | Start with `docs/docs-index.md` |
| `tools/` | Development integrations and supporting utilities | Keep changes within the tool's boundary |

More specific `AGENTS.md` files override this guide within their directories.

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

For non-trivial work where existing behaviour or project boundaries matter,
use the `flowform-doc-context` skill and the `flowform-docs` MCP server to load
focused context from `docs/`. Read only the relevant documents and verify their
claims against the repository. Surface Docsys reliability warnings before
presenting affected claims as current, and report confirmed contradictions
instead of silently choosing one source.

After behavioural or architectural changes, review the impacted documentation.
Update only pages whose meaning changed, and regenerate generated documentation
instead of editing it manually. After reviewing implementation-backed claims,
use `docsys evidence promote --staged` to record their staged evidence; the
pre-commit hook enforces verification drift. Treat `old-docs/` as historical
material.

Codex and Claude provide a `docs-maintainer` specialist for bounded
documentation work. The parent agent remains responsible for integration and
final validation.

## Handoff

Summarize what changed, what was validated, and any remaining gaps or
assumptions. Do not commit or push unless the user explicitly requests it.
