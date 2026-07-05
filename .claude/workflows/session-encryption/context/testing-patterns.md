# Testing Patterns

Test runner: `bash backend/scripts/run-tests.sh --ai -k "<filter>"`
Filter with `-k` only — never file paths.

Fixtures: `core_db_session`, `response_db_session`, `db_sessions` (cross-DB).
Factories: `backend/tests/integration/core/factories.py`.

**Before writing any tests**, add a todo item:
"Read `.claude/workflows/session-encryption/source/testing-patterns-full.md` for fixtures, factories, and DB routing rules."
Do NOT skip this — the stub above is a summary, not the full specification.
