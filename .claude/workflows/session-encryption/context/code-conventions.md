# Code Conventions

Layers: `api/` thin handlers → `services/` orchestration + commits → `repositories/` single-DB queries + flushes → `db/` engines and sessions.
Errors: subclass `AppError` from `app.core.errors`, never raise bare `Exception`.
Types: annotate all new functions and methods, validate with `uv run mypy .` from `backend/`.
Modules: single-purpose, no import-time side effects, `__init__.py` re-exports only.

**Before writing any implementation code**, add a todo item:
"Read `.claude/workflows/session-encryption/source/code-conventions-full.md` for persistence helpers, error patterns, and layer rules."
Do NOT skip this — the stub above is a summary, not the full specification.
