---
paths: backend/app/api/v1/**
---

# backend/app/api/v1/

API v1 = HTTP boundary. Route handlers translate req → service calls → serialize results.

Route files thin:

- declare route + OpenAPI metadata
- parse body/query/path inputs
- resolve auth + request-scoped DB sessions
- call service or health/readiness helper
- return JSON with `model_dump(mode="json")` when using Pydantic

No SQL, policy branching, workflow coordination in route handlers.
`__init__.py` = blueprint wiring + imports only.