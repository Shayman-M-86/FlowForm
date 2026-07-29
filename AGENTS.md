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

Documentation is optional context, not a task-start requirement. Use
`flowform-doc-context` only for explicit documentation work or after finding a
material documentation gap. Implementation and tests remain authoritative.
Review documentation impact once after relevant behaviour settles, and use
`flowform-doc-verification` only when the user explicitly approves promotion
and staging.

## Handoff

Summarize what changed, what was validated, and any remaining gaps or
assumptions. Do not commit or push unless the user explicitly requests it.
