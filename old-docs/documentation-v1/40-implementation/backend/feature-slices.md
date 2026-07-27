---
title: Backend feature slices
aliases:
  - "Backend feature slices"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: cd9bd50
tags: [backend]
related_code:
  - "../../../backend/app/api/v1/"
  - "../../../backend/app/schema/api/"
  - "../../../backend/app/services/"
  - "../../../backend/app/repositories/"
  - "../../../backend/openapi.yaml"
  - "../../../scripts/ci/sync-openapi.sh"
related_docs:
  - "Backend implementation guides"
  - "Backend code organization"
  - "Testing workflow"
  - "Database migrations"
---

# Backend feature slices

Provides a repeatable way to construct a backend change without collapsing its
HTTP, application, and persistence responsibilities into one file.

## A typical endpoint change

```text
API schema -> route -> service/domain policy -> repository -> ORM/SQL schema
       \-> OpenAPI export -> frontend generated consumers (when the contract changes)
```

The exact modules depend on the feature. A read-only operation may only need a
route, schema, and repository. A cross-store or encryption-sensitive operation
normally needs a service boundary and explicit failure handling.

## Implementation sequence

1. Identify the owning API blueprint in `api/v1/` and the applicable core or
   response store.
2. Define or update a Pydantic API request/response model under `schema/api/`.
   Do request-shape validation there; leave state-dependent or authorization
   checks to the service/domain layer.
3. Add a thin route that invokes the appropriate service and turns its result
   into the declared response contract.
4. Add or extend a service when the operation coordinates policy, permissions,
   multiple repositories, encryption, or transaction boundaries.
5. Add focused repository methods for database interaction. Keep query details
   out of the route.
6. If storage changes, update the canonical SQL initialization schema as well
   as the matching ORM mapping. See [[database-migrations|Database migrations]].
7. If the public API contract changes, regenerate it and its consumers with
   `bash scripts/ci/sync-openapi.sh`; do not hand-edit `backend/openapi.yaml`.
8. Validate the affected tests and static/contract checks using
   [[testing|Testing workflow]].

## Route shape

Keep a route focused on its transport concern. This is illustrative pseudocode,
not a copy-and-paste API:

```python
@blueprint.post("/resources")
@require_authenticated_user
def create_resource():
    request_model = CreateResourceRequest.model_validate(request.get_json())
    result = resource_service.create(actor=current_actor(), request=request_model)
    return CreateResourceResponse.model_validate(result).model_dump(), 201
```

The important split is intentional: Pydantic owns request shape, the service
owns the use case, repositories own persistence, and the response model owns
the HTTP output contract.

## Test by boundary

| Change | Minimum focused proof |
| --- | --- |
| API schema or route | request/response contract and route behaviour |
| service/domain policy | unit test for outcomes and important failures |
| repository or ORM | integration coverage against the appropriate database |
| core/response schema | rebuilt disposable databases plus structural constraint coverage |
| API contract | OpenAPI/frontend generated-output drift check |

Do not make a unit test depend on private call order simply because the current
service happens to call helpers in that order. Prefer observable contracts and
failure behaviour.

## Related documents

- [[40-implementation/backend/README|Backend implementation guides]]
- [[code-organization|Backend code organization]]
- [[testing|Testing workflow]]
- [[database-migrations|Database migrations]]
