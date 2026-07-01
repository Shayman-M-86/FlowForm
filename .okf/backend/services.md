---
type: Service
title: backend/app/services/
description: The backend's use-case layer — orchestrates domain rules, repositories, and transactions without HTTP knowledge.
resource: backend/app/services/
tags: [backend, flask, service-layer]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

Services are the only place where cross-database orchestration is allowed
(see [two-database-model](/architecture/two-database-model.md)). A well-formed
service:

- accepts typed inputs, ids, sessions, and actor context
- loads and persists through [repositories](/backend/repositories.md)
- calls [app.domain](/backend/domain.md) for policy and business decisions
- coordinates multi-step workflows in one place
- owns commits and transaction boundaries
- returns ORM rows or small result objects

Services are grouped by use case. API-facing services may delegate to
smaller core services, but [routes](/backend/api-v1.md) must never become the
workflow layer.

Avoid services that are just renamed repositories, and avoid repositories
that quietly perform service-level coordination — this boundary is
deliberately strict (see [layer-check skill](../../backend/CLAUDE.md)).

# Citations

[1] [.claude/rules/repomap/backend-app-services.md](../../.claude/rules/repomap/backend-app-services.md)
