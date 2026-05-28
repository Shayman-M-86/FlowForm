---
paths: backend/app/api/v1/**
---

# backend/app/api/v1/

_Last updated: 2026-05-27 by /repomap_

Flask Blueprint route handlers for v1 of the REST API, organised into auth.py, me.py, public.py, health.py, and a projects/ sub-package. Every route is decorated with @openapi_route (supplying request/response Pydantic models and tags for OpenAPI generation) and @auth.require_auth() or @auth.optional_auth() for JWT enforcement. Handlers are intentionally thin: they call parse()/parse_query() for request validation, obtain db sessions via get_core_db()/get_response_db(), delegate to a service, then serialize via Pydantic's model_dump(mode='json'). public.py is the unauthenticated surface for form-fillers: it exposes survey lookup by public slug, link resolution, and both slug- and link-based submission creation.
