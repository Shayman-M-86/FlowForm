# FlowForm Backend Guide

Flask API for the FlowForm platform. See the root [CLAUDE.md](../CLAUDE.md)
for architecture, layer rules, database separation, and saga workflow docs.

---

## Stack

- **Python 3.14+** with **uv**
- **Flask 3** blueprints
- **SQLAlchemy 2** synchronous declarative ORM
- **Pydantic v2** request/response schemas
- **Auth0** RS256 JWTs via JWKS; scopes via `@auth.require_auth(scope)`
- **PostgreSQL** split into `core` and `response`
- **mypy + ruff** for type checks and linting

Secrets come from environment variables. Never hardcode credentials.

---

## Commands

```bash
uv run flask run                        # dev server
uv run ruff check .                     # lint
uv run ruff format .                    # format
uv run mypy .                           # type check
```

### Tests

Tests run inside Docker. Use `--ai` for compact output. Default to full
rebuild + teardown.

```bash
bash backend/scripts/run-tests.sh --ai
bash backend/scripts/run-tests.sh --ai -k "test_submission_gateway"
```

Use `-k` for filtering. Do not pass file paths as filters.

Other useful flags for `run-tests.sh`:

- `--logs=all` prints Docker logs from all services on failure
- `--verbose` prints full output without the spinner

### Schema checks

Keep `db/error_handling/integrity_rules.py` aligned with real Postgres
constraint names. The database is built from SQL schema files, not ORM
metadata, so stale rule names can turn expected 409s into 500s.

```bash
bash backend/scripts/check-integrity-rule-constraints.sh
bash backend/scripts/check-integrity-rule-constraints.sh --keep   # leave the container running
```

The script runs from any cwd, requires Docker and `uv`, and uses a throwaway
`postgres:17` container. Dead rules and type mismatches fail; unmapped
constraints are advisory.

---

## Auth

Protect routes with `@auth.require_auth()` or `@auth.optional_auth()` for
public endpoints. Middleware verifies Bearer tokens against Auth0 JWKS, stores
claims on `flask.g`, and exposes the Auth0 subject through
`auth.get_current_user_sub()`.

---

## Conventions

- Type hints everywhere; keep mypy clean
- Pydantic schemas live in `schemas/`; never import ORM models into them
- Routes stay thin: no SQL, no business logic
- Cross-db orchestration belongs in `services/` only
- Only `db/` touches engines, sessions, transaction helpers, or raw connection
  objects
