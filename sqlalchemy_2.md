# Branch: feat/sqlalchemy-db-manager — Replace Flask-SQLAlchemy with SQLAlchemy 2.0

## Summary

Removed Flask-SQLAlchemy and introduced a custom `DatabaseManager` using SQLAlchemy 2.0 with **two explicit databases** (core + response), each with its own engine and session.

## Commits

1. `70c84ba` — Core migration (12 files, +229/-110)
2. `28bdee6` — Simplify session management: removed nested functions from `init_db_sessions`
3. `5b07782` — Fix: removed redundant `teardown_request` call in `session.py`

## Files changed

| File | Change |
| --- | --- |
| `app/db/__init__.py` | Public re-exports: `get_core_db`, `get_response_db`, `commit_or_rollback`, `rollback_safely` |
| `app/db/manager.py` | New `DatabaseManager` class |
| `app/db/session.py` | Request-scoped session lifecycle (`open_request_sessions`, `close_request_sessions`, `init_db_sessions`) |
| `app/db/context.py` | `get_core_db()` / `get_response_db()` — reads sessions from Flask `g` |
| `app/db/transaction.py` | `commit_or_rollback()` / `rollback_safely()` helpers |
| `app/db/engine.py` | Removed |
| `app/db/init_models.py` | Removed |
| `app/core/extensions.py` | Replaced `db = SQLAlchemy()` with `db_manager = DatabaseManager()` |
| `app/core/config.py` | Removed `SQLALCHEMY_DATABASE_URI` / `SQLALCHEMY_BINDS` |
| `app/core/factory.py` | Added `init_db_sessions(app)` call; added model import to register metadata |
| `tests/integration/conftest.py` | New fixtures: `core_connection`, `response_connection`, `core_db_session`, `response_db_session`, `db_session` (compat), `db_sessions` (NamedTuple) |
| `tests/integration/response/test_db_routing.py` | Updated to use `db_manager` directly |

## Architecture

### DatabaseManager (`app/db/manager.py`)

- Initialised once at startup via `init_app(app)` (Flask extension pattern)
- Holds two engines (`core_engine`, `response_engine`) and two sessionmakers
- `pool_pre_ping=True`, `autoflush=False`, `autocommit=False`, `expire_on_commit=False`
- `dispose()` for clean teardown

### Request lifecycle (`app/db/session.py`)

- `before_request` → `open_request_sessions()` — creates `g.core_db` and `g.response_db`
- `teardown_request` → `close_request_sessions(exception)` — rolls back if exception, then closes both sessions

### Public API (`app/db/__init__.py`)

```python
from app.db import get_core_db, get_response_db, commit_or_rollback, rollback_safely
```

## Usage

### Routes

```python
from app.db import get_core_db, get_response_db

core_db = get_core_db()
response_db = get_response_db()
```

### Services (dependency injection via constructor)

```python
class Service:
    def __init__(self, *, core_db, response_db):
        self.core_db = core_db
        self.response_db = response_db
```

### Transaction helpers

```python
from app.db import commit_or_rollback, rollback_safely

commit_or_rollback(core_db)           # commit or rollback+reraise
rollback_safely(core_db, response_db) # silent rollback of multiple sessions
```

## Tests

Tests use connection-level transactions for isolation: each fixture opens a raw connection, begins a transaction, and rolls it back after the test (no data persists).

### Fixtures (`tests/integration/conftest.py`)

```python
def test_core_only(core_db_session):
    core_db_session.add(...)

def test_response_only(response_db_session):
    response_db_session.add(...)

def test_both(db_sessions):
    db_sessions.core.add(...)
    db_sessions.response.add(...)

# Legacy compatibility (single session, routes by base class)
def test_legacy(db_session):
    db_session.add(...)   # routes CoreBase models to core, ResponseBase to response
```

`db_sessions` is a `NamedTuple` with `.core` and `.response` fields. It also supports positional unpacking: `core, response = db_sessions`.

## Notes

- No global session
- No implicit binds — services must receive sessions explicitly
- Models must be imported before migrations/metadata operations to register with SQLAlchemy
- `flask-sqlalchemy` should be removed from `pyproject.toml` dependencies (still listed, now unused)
- `future=True` in `create_engine` is a no-op in SQLAlchemy 2.0 (2.0-style engine is the default)
