---
paths: backend/tests/**
---

# backend/tests/

_Last updated: 2026-05-27 by /repomap_

The test suite is split into `unit/` and `integration/` subdirectories, each with its own `conftest.py`. Unit tests cover services and route handlers (e.g. `test_auth_service.py`, `test_members_service.py`, `test_account_service.py`, `test_public_link_validation.py`) using monkeypatching — for example, Firebase `verify_id_token` is patched to control token verification. Integration tests exercise the ORM layer directly against real database sessions, validating DB constraints (CHECK, FK, NOT NULL, UNIQUE violations via `psycopg.errors`) for models such as `SurveySubmission`, `SurveyQuestion`, and auth bootstrap flows; factory helpers in `tests/integration/core/factories.py` construct valid ORM objects for fixtures.
