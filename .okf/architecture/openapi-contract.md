---
type: API Contract
title: OpenAPI-driven API contract
description: The backend generates an OpenAPI 3.1 spec at runtime; frontend TypeScript types are generated from it, keeping the contract as the single source of truth.
resource: /openapi.json
tags: [backend, frontend, api, openapi]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

The backend builds an OpenAPI 3.1 spec at runtime from Pydantic models and
lightweight `@openapi_route` metadata attached to Flask view functions in
[backend/app/api/v1/](/backend/api-v1.md). The decorator is documentation-only
and records summary, tags, request model, response model, and auth mode. The
spec builder combines this registry with the live Flask URL map and serves:

- `/openapi.json` — raw JSON for tooling
- `/docs` — Swagger UI for browsing

Frontend TypeScript types in `studio-app/src/api/generated/schema.ts` are
generated from the spec with `openapi-typescript`. The [Studio app](/apps/studio-app.md)
must not hand-write competing request/response types.

# Error shape

All API errors use a shared response shape:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {}
}
```

Validation failures include Pydantic field errors under `details.errors[]`.

# Discovery

Agents should discover the live API surface through the `flowform-openapi`
MCP tool (see [flowform-openapi MCP server](/tools/flowform-openapi-mcp.md))
rather than grepping for handlers or guessing shapes from existing frontend
code, since that risks copying a stale type.

# Citations

[1] [Root CLAUDE.md — API and OpenAPI](../../CLAUDE.md)
[2] [frontend/CLAUDE.md — Discovering the API](../../frontend/CLAUDE.md)
