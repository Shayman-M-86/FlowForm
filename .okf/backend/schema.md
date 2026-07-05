---
type: Service
title: backend/app/schema/
description: Pydantic API contracts and SQLAlchemy ORM mappings, kept as two distinct halves.
resource: backend/app/schema/
tags: [backend, pydantic, sqlalchemy]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

- `api/` holds Pydantic request/response contracts, which back the
  [OpenAPI contract](/architecture/openapi-contract.md).
- `orm/` holds SQLAlchemy mappings.
- `enums.py` and `api/limits.py` keep shared contract values explicit.

SQL schema files (in `infra/postgres/init/schema/`) are the migration
source of truth. ORM metadata only models what the app needs for
relationships, flush behavior, and local validation — it is not a second
migration system.

**Never import ORM models into Pydantic schemas.** This keeps the API
contract stable even when persistence details move underneath it.

# Citations

[1] [.claude/rules/repomap/backend-app-schema.md](../../.claude/rules/repomap/backend-app-schema.md)
[2] [backend/CLAUDE.md — Conventions](../../backend/CLAUDE.md)
