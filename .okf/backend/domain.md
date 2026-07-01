---
type: Service
title: backend/app/domain/
description: Durable business rules reusable from services, with no HTTP knowledge.
resource: backend/app/domain/
tags: [backend, flask, business-rules]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

`app/domain` holds:

- policy checks and `ensure_*` guards
- typed domain errors
- shared permission/rule constants (feeding the RBAC model in [Auth](/architecture/auth.md))
- small pure decisions that would otherwise be duplicated across [services](/backend/services.md)

Prefer pure checks over DB work here. If a rule needs data, keep the lookup
narrow and let services coordinate the full workflow.

# Citations

[1] [.claude/rules/repomap/backend-app-domain.md](../../.claude/rules/repomap/backend-app-domain.md)
