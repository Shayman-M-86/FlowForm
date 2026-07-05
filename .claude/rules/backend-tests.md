---
paths: backend/tests/**/*.py
---

# Backend test rules

Use backend test runner, keep output compact:

```bash
bash backend/scripts/run-tests.sh --ai
bash backend/scripts/run-tests.sh --ai -k "test_name"
```

- Filter w/ `-k`, not file paths.
- Prefer full runner unless narrower cmd already established.

## Session fixtures

| Fixture | Use for |
|---|---|
| `db_sessions` | Gateway / service tests (`DbSessions(core=..., response=...)`) |
| `core_db_session` | Core-only tests |
| `response_db_session` | Response-only tests |
| `db_session` | Legacy single-session tests only |

Fixture transactions savepoint-backed; test commits must not leak state.