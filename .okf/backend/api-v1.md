---
type: Service
title: backend/app/api/v1/
description: The HTTP boundary — thin Flask route handlers that translate requests into service calls and serialize results.
resource: backend/app/api/v1/
tags: [backend, flask, routes]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

API v1 is the HTTP boundary of the Flask app. Route handlers:

- declare the route and its `@openapi_route` metadata (used to build the
  [OpenAPI contract](/architecture/openapi-contract.md))
- parse body/query/path inputs
- resolve auth (`@auth.require_auth(scope)` / `@auth.optional_auth()`, see
  [Auth](/architecture/auth.md)) and request-scoped DB sessions
- call a [service](/backend/services.md) or a health/readiness helper
- return JSON, serializing Pydantic models with `model_dump(mode="json")`

Routes must not contain SQL, policy branching, or workflow coordination —
that belongs in [services/](/backend/services.md) and [domain/](/backend/domain.md).
`__init__.py` in this directory is blueprint wiring and imports only.

# Citations

[1] [.claude/rules/repomap/backend-app-api-v1.md](../../.claude/rules/repomap/backend-app-api-v1.md)
