# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FlowForm is a dynamic form platform for building adaptive surveys and quizzes with conditional logic. Forms adapt in real time based on user responses via rule-based branching.

**Stack:** React SPA (frontend, not yet implemented) + Flask REST API (Python, backend) + two PostgreSQL databases.

## Commands

All backend commands run from the `backend/` directory. This project uses **`uv`** — never use `pip` directly.

### Setup

```bash
# Install dependencies (run from backend/)
uv sync --extra dev --extra test
```

### Running the backend (local, no Docker)

```bash
# From backend/
uv run flask --debug run --host 0.0.0.0 --port 5000
```

### Docker (full dev environment)

```bash
# From repo root — starts postgres-core, postgres-response, and backend
docker-compose -f infra/docker/docker-compose.dev.yml up -d
```

Docker secrets are read from `infra/docker/secrets/*.secret.txt` files (not committed).

### Testing

```bash
# From backend/
pytest tests                           # all tests
pytest tests -m unit                   # unit tests only
pytest tests -m integration            # integration tests only
pytest --cov=app tests                 # with branch coverage report
pytest tests/test_config.py            # single test file
```

### Linting & Type Checking

```bash
# From backend/
uv run ruff check .                    # lint
uv run ruff format .                   # format
uv run pyright
```

### Database Migrations (Flask-Migrate)

```bash
# From backend/
uv run flask db migrate -m "description"
uv run flask db upgrade
```

### Security Audit

```bash
bash backend/scripts/pip-audit.sh
```

## Architecture

### Application Factory (`backend/app/core/factory.py`)

`create_app()` runs in order:

1. Bootstrap logging (before config)
2. Load `Settings` from env vars via Pydantic
3. Create Flask app, set up full logging
4. `init_extensions` — SQLAlchemy, Flask-Migrate, CORS
5. `register_api_v1` — register blueprints
6. `register_rate_limiting` — in-memory IP-based rate limiter

### Configuration (`backend/app/core/config.py`)

Settings use **Pydantic-Settings** with prefix `FF_` and `__` as nested delimiter. Key env vars:

| Env Var                           | Purpose                                                                |
| --------------------------------- | ---------------------------------------------------------------------- |
| `FF_ENV`                          | Required: `dev`, `test`, or `prod`                                     |
| `FF_APP__DEBUG`                   | Enable Flask debug mode                                                |
| `FF_APP__SECRET_KEY`              | Flask secret key                                                       |
| `FF_DATABASE__*`                  | Core DB connection (user, host, port, name, password or password_file) |
| `FF_RESPONSE_DATABASE__*`         | Response DB connection (optional)                                      |
| `FF_AUTH0__DOMAIN` / `__AUDIENCE` | Auth0 config                                                           |
| `FF_RATE_LIMIT__*`                | Rate limiting settings                                                 |
| `FF_LOGGING__*`                   | Log levels, file output, JSON format                                   |

Settings are cached via `@lru_cache`. Use `current_settings()` inside Flask context or `get_settings()` outside.

Database passwords can be provided via `*__PASSWORD` (plain string) or `*__PASSWORD_FILE` (Docker secret file path).

### Two-Database Model

**Core DB** (`flowform_core`) — forms, questions, users, roles, RBAC, survey versions. Schema: `infra/postgres/init/schema/flowform_core_db_schema_v3.sql`

**Response DB** (`flowform_response`) — survey submissions and response payloads, isolated for privacy. Schema: `infra/postgres/init/schema/flowform_response_db_schema_v3.sql`

The response database is optional at startup (`response_database: DatabaseSettings | None`). Both databases are initialized via templated SQL scripts in `infra/postgres/init/` — the `FF_PGDB_INIT__TARGET` env var (`core` or `response`) controls which schema each container loads.

### API Blueprint Convention

All v1 blueprints register in `backend/app/api/v1/__init__.py`. The `register_api_v1` function enforces that every blueprint name ends with `_v1` and derives the URL prefix automatically: `health_v1` → `/api/v1/health`.

To add a new resource, create `backend/app/api/v1/<resource>.py` with a blueprint named `<resource>_v1`, then add it to the `ROUTES` list in `__init__.py`.

Current routes:

- `GET /api/v1/health/` — liveness check
- `GET /api/v1/health/ready` — readiness check

### Data Model Design

- Relational schema for forms, questions, users, roles (strong integrity)
- JSON columns for flexible rule definitions and response payloads
- Soft-delete for published survey versions (preserves response interpretation history)
- Hard-delete for all other entities

### Rate Limiting (`backend/app/middleware/rate_limit/`)

In-memory, per-IP, sliding-window algorithm. Configured via `FF_RATE_LIMIT__*`. Health endpoints are ignored by default.

## Testing Conventions

- Mark tests with `@pytest.mark.unit` or `@pytest.mark.integration`
- Both markers are required (strict mode — unmarked tests error)
- Integration tests hit real external services/databases; unit tests must not
- `filterwarnings = ["error"]` — warnings are treated as test failures

## Code Style

- **Ruff** for linting and formatting (line length: 100, Google docstring convention)
- Docstrings required on classes and public functions (not on `__init__`, module level, or test files)
- **mypy** for type checking (`check_untyped_defs = true`)
- Python 3.14+
