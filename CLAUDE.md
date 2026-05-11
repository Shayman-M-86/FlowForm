# FlowForm — Claude Code Guide

## What is FlowForm?

FlowForm is a survey platform. Teams use it to create and publish surveys,
collect responses from end users, and review the results. The **Studio** app
is the back-office dashboard where authenticated users manage projects,
design surveys, and track responses. The **Public Site** is what respondents
see — the form-filling experience delivered to end users.

The backend exposes a REST API consumed by both apps. Responses are stored
with privacy in mind: submission payloads are isolated in a separate database
and tied to respondents via a pseudonymous UUID rather than a real user ID.

---

## Repo layout

```
FlowForm/
├── backend/        Flask API — see backend/CLAUDE.md
└── frontend/       JS monorepo — see frontend/CLAUDE.md
    ├── apps/
    │   ├── studio-app/     Admin dashboard — see frontend/apps/studio-app/CLAUDE.md
    │   └── public-site/    Marketing + form-filler — see frontend/apps/public-site/CLAUDE.md
    └── packages/           Shared libs — see frontend/packages/CLAUDE.md
```

---

## Architecture in brief

**Backend** is a Flask app managed with **uv**. It uses two PostgreSQL
databases (`core` and `response`) with strict separation: `core` holds survey
structure and user data; `response` holds raw submission payloads. They are
linked only by a shared integer
(`core.survey_submissions.id ↔ response.submissions.core_submission_id`).
Cross-db orchestration lives exclusively in `services/`. The response DB
never stores a real `user_id` — only a stable pseudonymous UUID.

**Frontend** is a Vite/React 19 monorepo. Studio is an authenticated SPA for
survey management. Public site is the end-user form-filling experience.

---

## Sub-guides

| Area | Guide |
|---|---|
| Backend (Flask, DBs, layers) | [backend/CLAUDE.md](backend/CLAUDE.md) |
| Frontend monorepo | [frontend/CLAUDE.md](frontend/CLAUDE.md) |
| Studio app | [frontend/apps/studio-app/CLAUDE.md](frontend/apps/studio-app/CLAUDE.md) |
| Public site | [frontend/apps/public-site/CLAUDE.md](frontend/apps/public-site/CLAUDE.md) |
| Shared packages | [frontend/packages/CLAUDE.md](frontend/packages/CLAUDE.md) |
