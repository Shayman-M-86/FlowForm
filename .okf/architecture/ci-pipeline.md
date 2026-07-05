---
type: Playbook
title: CI pipeline
description: GitHub Actions pipeline run on push/PR to main — security audit, dockerized backend tests, frontend build, coverage artifact.
tags: [ci, testing, backend, frontend]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

GitHub Actions runs on push and pull request to `main` with four stages:

1. **Security checks** — backend dependency/security audit (`pip-audit`)
2. **Backend tests** — pytest inside Docker against two real PostgreSQL
   databases (`core` and `response`), no mocked DB layer. See
   [backend/tests/](/backend/tests.md).
3. **Frontend build** — installs dependencies and builds both
   [studio-app](/apps/studio-app.md) and [public-site](/apps/public-site.md)
4. **Coverage artifact** — backend test coverage uploaded as an artifact

# Why this matters

Backend tests use real databases rather than mocks, which gives stronger
confidence in constraints, transactions, and the cross-database
orchestration described in [two-database-model](/architecture/two-database-model.md).

# Local equivalent

```bash
bash backend/scripts/run-tests.sh --ai
bash backend/scripts/run-tests.sh --ai -k "test_name"
```

# Citations

[1] [Root CLAUDE.md — CI](../../CLAUDE.md)
