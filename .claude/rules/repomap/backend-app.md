---
paths: backend/app/**
---

# backend/app/

_Last verified: 2026-06-15_

Top-level Flask app package. Entry point: `create_app` in `core/factory.py`.

Factory order:

- bootstrap logging/settings
- build Flask app + apply config
- init extensions: DB manager, Auth0 auth, URL converters, CORS
- init per-request core + response DB sessions
- register API v1 blueprints
- register rate limiting
- register error handlers + OpenAPI options
- import ORM package so SQLAlchemy mappings register
- seed required permission rows

Layer map:

- `api/` -> thin Flask routes + request parsing
- `core/` -> config, extension singletons, app factory
- `db/` -> engines, sessions, transaction/error helpers, ORM bases
- `domain/` -> policy guards + typed errors
- `repositories/` -> SQLAlchemy data access
- `schema/` -> Pydantic API contracts + ORM models
- `services/` -> orchestration, commits, permission/session flows
- `middleware/` -> auth, rate limit, URL converters
- `openapi/` -> route metadata + spec generation/export
- `logging/` -> bootstrap/app/request/audit logging
- `utils/` -> small shared helpers

Keep direction clean: routes -> services -> domain/repositories/schema. `gateway/`
has no active source files in current checkout; do not add new gateway code
without re-establishing its boundary.
