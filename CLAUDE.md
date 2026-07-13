# FlowForm Claude Guide

## What Is FlowForm?

FlowForm is a survey platform for creating surveys, publishing them, collecting
responses, and reviewing results.

- **Studio** is the authenticated dashboard for project and survey management.
- **Public Site** is the respondent-facing form experience.
- **Backend** is the REST API used by both apps.

---

## Repo Layout

```text
FlowForm/
├── backend/        Flask API - see backend/CLAUDE.md
└── frontend/       JS monorepo - see frontend/CLAUDE.md
    ├── apps/
    │   ├── studio-app/     Admin dashboard - see frontend/apps/studio-app/CLAUDE.md
    │   └── public-site/    Marketing + form-filler - see frontend/apps/public-site/CLAUDE.md
    └── packages/           Shared libs - see frontend/packages/CLAUDE.md
```

---

## Architecture

**Backend:** Flask with `uv`, PostgreSQL split into `core` and `response`
with no cross-db SQL foreign keys — the two sides are linked via
HMAC-derived opaque locators, and cross-db work is kept in `services/`. See
[docs/session-encryption/](docs/session-encryption/) for the full model and
[backend/CLAUDE.md](backend/CLAUDE.md) for backend details.

**Frontend:** Vite/React 19 monorepo. Studio handles authenticated survey
management; Public Site handles form delivery and response capture.

---

## Sub-guides

| Area | Guide |
|---|---|
| Backend (Flask, DBs, layers) | [backend/CLAUDE.md](backend/CLAUDE.md) |
| Frontend monorepo | [frontend/CLAUDE.md](frontend/CLAUDE.md) |
| Studio app | [frontend/apps/studio-app/CLAUDE.md](frontend/apps/studio-app/CLAUDE.md) |
| Public site | [frontend/apps/public-site/CLAUDE.md](frontend/apps/public-site/CLAUDE.md) |
| Shared packages | [frontend/packages/CLAUDE.md](frontend/packages/CLAUDE.md) |

---

## Documentation context

Before implementation work that touches existing FlowForm architecture,
behaviour, workflows, or domain rules, load focused context from the
`flowform-docs` MCP server (`get_task_context`) instead of grepping the docs
tree or reading large parts of the repo. See [AGENTS.md](AGENTS.md) for the
rules and the `flowform-doc-context` skill for the workflow. Code, tests,
schemas, config, and infrastructure remain the source of truth; skip retrieval
for trivial edits (spelling, formatting, mechanical renames).
