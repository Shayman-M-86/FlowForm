---
paths: backend/tests/**/*.py
---

# Backend test rules

Always run tests with the `--ai` flag for compact output:

```bash
bash backend/scripts/run-tests-rebuild-teardown.sh --ai
bash backend/scripts/run-tests-rebuild-teardown.sh --ai -k "test_name"
```

- Filter with `-k` only — never pass file paths as filters
- `run-tests-rebuild-teardown.sh` — full rebuild + teardown, clean state; use this by default
- `run-tests-fast.sh` — reuses running containers; only for tight local iteration

## Session fixtures

| Fixture | Use for |
|---|---|
| `db_sessions` | Gateway / service tests (`DbSessions(core=..., response=...)`) |
| `core_db_session` | Core-only tests |
| `response_db_session` | Response-only tests |
| `db_session` | Legacy single-session tests only |

All sessions use savepoints — commits release savepoints, outer transaction rolls back on teardown.
