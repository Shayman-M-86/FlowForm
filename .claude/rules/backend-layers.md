---
globs: backend/app/**/*.py
---

# Backend layer rules

Enforce the layer stack — each layer has one job:

- `models/` — pure SQLAlchemy ORM, no business logic, no cross-db relationships
- `db/` — engines, sessions, transaction helpers only; nothing else imports engine/connection objects
- `repositories/` — named query helpers, one DB per repo, no cross-db coordination
- `services/` — the only layer that touches both databases; all saga workflows go here
- `schemas/` — Pydantic only; never import from `models/`
- `api/routes/` — thin HTTP handlers; call a service, return a response; no SQL, no business logic

Cross-db orchestration belongs in `services/` exclusively. Routes must not contain SQL or session management.

The response DB must never receive a real `user_id` — only a `pseudonymous_subject_id` UUID.

`models/core/` uses `CoreBase`; `models/response/` uses `ResponseBase` — never mixed.
