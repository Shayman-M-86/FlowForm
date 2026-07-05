# FlowForm Backend - Codex Guide

Flask API for the FlowForm platform. See the root [AGENTS.md](../AGENTS.md)
for architecture, layer rules, two-database design, and saga workflow docs.

---

## Stack

- **Python 3.14+**, managed with **uv**
- **Flask 3** - Blueprint-based route organisation
- **SQLAlchemy 2** - synchronous, declarative ORM models
- **Pydantic v2** - request/response validation
- **Auth0** - JWT access tokens (RS256), verified via JWKS; scope enforcement
  via `@auth.require_auth(scope)` decorator
- **PostgreSQL** - two separate databases (`core` and `response`)
- **Pyright + Ruff** - type checking and linting

All secrets come from environment variables; never hardcode credentials.

---

## Commands

```bash
uv run flask run                        # dev server
uv run ruff check .                     # lint
uv run ruff format .                    # format
uv run pyright                          # type check
```

### Running tests

Tests run inside Docker. Always use `--ai` for compact output.

**Full rebuild + teardown** - clean state every run, use this by default:

```bash
bash backend/scripts/run-tests.sh --ai
bash backend/scripts/run-tests.sh --ai -k "test_submission_gateway"
```

Filter with `-k` only - never pass file paths as filters.

Other useful flags for `run-tests.sh`:

- `--logs=all` - print Docker logs from all services on failure
- `--verbose` - full output, no spinner

---

## Auth flow

Routes are protected with `@auth.require_auth()` (or `@auth.optional_auth()`
for public endpoints). The middleware verifies Bearer tokens against Auth0's
JWKS endpoint, extracts claims, and stores them on `flask.g`. Use
`auth.get_current_user_sub()` inside a route to get the Auth0 subject ID.

---

## Conventions

- Type hints everywhere; keep Pyright clean
- Pydantic schemas live in `schemas/` - never import ORM models into them
- Routes stay thin - no SQL, no business logic
- Cross-db orchestration belongs in `services/` only
- `db/` layer owns engines, sessions, and transaction helpers - nothing else
  should touch SQLAlchemy engine or connection objects directly
