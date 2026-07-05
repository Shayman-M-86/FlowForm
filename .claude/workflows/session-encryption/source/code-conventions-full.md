# Code Conventions — Full Reference

## Backend typing

- Type new and changed functions, methods, and service result objects.
- Prefer precise project types; use `Any` only at unavoidable external boundaries.
- Validate from `backend/` with `uv run mypy .` when typing-sensitive code changes, but do not describe the repo as mypy-strict unless a strict mypy config is added and the full run is clean.

## Errors

- API-visible and domain failures should be named `AppError` subclasses from `app.core.errors`.
- `AppError` is `@dataclass(slots=True)` with `status_code`, `code`, `message`, and `details`.
- Expected failures should not raise bare `Exception`; add a focused error class in the relevant `errors.py`.
- Keep error codes stable string constants on concrete errors. `AuthError` is the existing parameterized base exception.

## Layers

- `api/` handlers translate HTTP/auth/request data into service calls and return response models plus status codes. No SQL or business rules.
- `repositories/` accept a `Session`, touch one database, and return ORM rows, scalars, or simple collections. No commits.
- `services/` orchestrate workflows, call repositories/domain rules, coordinate cross-database work, own transaction boundaries, and commit.
- `domain/` owns policy decisions and rule language when logic is more than simple persistence orchestration.
- `db/` owns engines, sessions, transaction helpers, and database error translation.

## Persistence

- Use `db.scalar()` / `db.scalars()` for reads and `db.add()` for inserts.
- Repositories usually flush with `flush_with_err_handle(db, contexts=[row])` after mutations that should translate integrity errors.
- Services commit with `commit_with_err_handle(db, contexts=[...])`.
- Direct `db.commit()` / `db.flush()` exists in a few older or low-level paths; do not copy it into new feature code without a specific reason.

## Modules

- Keep modules single-purpose.
- `__init__.py` files re-export public surfaces only.
- Avoid import-time side effects: no network calls, file I/O, random values, or database access.
- Pydantic/API schemas live in `schemas/`; do not import ORM models into schema definitions.
