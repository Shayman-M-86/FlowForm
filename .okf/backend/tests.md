---
type: Playbook
title: backend/tests/
description: Backend tests grouped by how much runtime they exercise — unit, integration, and e2e.
resource: backend/tests/
tags: [backend, testing]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

- `unit/` isolates one behavior with fakes or monkeypatching.
- `integration/` uses real database fixtures for persistence and service edges.
- `e2e/` goes through Flask routes, auth seams, [services](/backend/services.md),
  [repositories](/backend/repositories.md), and the test DB.

Put new tests at the lowest scope that still proves the behavior.

# Running tests

```bash
bash backend/scripts/run-tests.sh --ai
bash backend/scripts/run-tests.sh --ai -k "test_submission_gateway"
```

Use `-k` to filter tests — do not pass file paths as filters. Tests run
inside Docker against real PostgreSQL databases, matching the
[CI pipeline](/architecture/ci-pipeline.md).

# Citations

[1] [.claude/rules/repomap/backend-tests.md](../../.claude/rules/repomap/backend-tests.md)
[2] [backend/CLAUDE.md — Tests](../../backend/CLAUDE.md)
