---
paths: backend/tests/**
---

# backend/tests/

Backend tests are grouped by how much runtime they exercise.

- `unit/` isolates one behavior with fakes or monkeypatching.
- `integration/` uses real database fixtures for persistence and service edges.
- `e2e/` goes through Flask routes, auth seams, services, repos, and the test DB.

Put new tests at the lowest scope that still proves the behavior. Keep fixture
mechanics and runner details in the general backend test rule.
