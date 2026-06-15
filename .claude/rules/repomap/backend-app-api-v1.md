---
paths: backend/app/api/v1/**
---

# backend/app/api/v1/

_Last verified: 2026-06-15_

API v1 Flask Blueprint handlers. Keep thin:

- contract -> `@openapi_route`
- input -> `parse()` / `parse_query()`
- DB session -> `get_core_db()` / `get_response_db()`
- work/policy -> services
- JSON -> `model_dump(mode="json")`

Auth:

- protected project/me/auth -> `@auth.require_auth()`
- public respondent -> `auth_required=False`
- anon+auth same public endpoint -> `@auth.optional_auth()`
- `health.py` -> no auth, direct DB readiness

`projects/` -> one `projects_bp`. `__init__.py` owns service singletons + imports
route submodules. Temp helpers stay outside main route files when possible:
public submission-session stubs, admin response stubs.
