# FlowForm - Codex Guide

## What is FlowForm?

FlowForm is a survey platform. Teams use it to create and publish surveys,
collect responses from end users, and review the results. The **Studio** app
is the back-office dashboard where authenticated users manage projects,
design surveys, and track responses. The **Public Site** is what respondents
see - the form-filling experience delivered to end users.

The backend exposes a REST API consumed by both apps. Responses are stored
with privacy in mind: submission payloads are isolated in a separate database
and linked back via HMAC-derived opaque locators rather than a shared key or
a real user ID.

---

## Repo layout

```text
FlowForm/
├── backend/        Flask API - see backend/AGENTS.md
└── frontend/       JS monorepo - see frontend/AGENTS.md
    ├── apps/
    │   ├── studio-app/     Admin dashboard - see frontend/apps/studio-app/AGENTS.md
    │   └── public-site/    Marketing + form-filler - see frontend/apps/public-site/AGENTS.md
    └── packages/           Shared libs - see frontend/packages/AGENTS.md
```

---

## Architecture in brief

**Backend** is a Flask app managed with **uv**. It uses two PostgreSQL
databases (`core` and `response`) with strict separation: `core` holds survey
structure, subjects, and session metadata; `response` holds only encrypted
answer payloads. There are no cross-db SQL foreign keys - the two sides are
linked via HMAC-derived opaque locators (`session_locator`, `answer_locator`)
computed from a versioned linkage secret. See
[docs/session-encryption/](docs/session-encryption/) for the full model.
Cross-db orchestration lives exclusively in `services/`. The response DB
never stores a real user ID, project ID, or survey ID.

**Frontend** is a Vite/React 19 monorepo. Studio is an authenticated SPA for
survey management. Public site is the end-user form-filling experience.

---

## Sub-guides

| Area | Guide |
|---|---|
| Backend (Flask, DBs, layers) | [backend/AGENTS.md](backend/AGENTS.md) |
| Frontend monorepo | [frontend/AGENTS.md](frontend/AGENTS.md) |
| Studio app | [frontend/apps/studio-app/AGENTS.md](frontend/apps/studio-app/AGENTS.md) |
| Public site | [frontend/apps/public-site/AGENTS.md](frontend/apps/public-site/AGENTS.md) |
| Shared packages | [frontend/packages/AGENTS.md](frontend/packages/AGENTS.md) |
