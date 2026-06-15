---
paths: backend/tests/**
---

# backend/tests/

_Last verified: 2026-06-15_

Backend tests split by scope:

- `unit/` -> services, route contracts, OpenAPI/spec, schema limits; use
  monkeypatch/fakes, no real DB unless explicit.
- `integration/` -> real Postgres sessions in savepoint-backed fixtures; covers
  core/response ORM routing, constraints, factories, and service/repository
  behavior.
- `e2e/` -> Flask test client through route -> auth/RBAC -> service -> repo ->
  real DB; patches Auth0 token verification and DB session factories.

Root `conftest.py` builds app once, opens core + response connections, and
provides `core_db_session`, `response_db_session`, plus legacy multi-bind
`db_session`. Core factories live in `tests/integration/core/factories.py`.
Run via `backend/scripts/run-tests.sh`; it uses `uv run`, Docker test stack,
smart rebuild fingerprints, and passes extra args to pytest.
