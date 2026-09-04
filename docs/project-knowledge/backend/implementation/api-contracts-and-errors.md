---
title: Backend API contracts and errors
aliases: ["Backend API contracts and errors", "Backend API contract model", "API error normalization"]
document_type: implementation
status: verified
authority: canonical
verified_evidence_digest: sha256:409a7c78fb6a4f5c8d1896dffb050f5f2a1242815bcc410431718284809e17b5
last_edited: 2026-09-05
tags: [backend, frontend]
related_code:
  - "../../../../backend/app/api/utils/validation.py"
  - "../../../../backend/app/api/utils/errors.py"
  - "../../../../backend/app/openapi/registry.py"
  - "../../../../backend/app/openapi/spec.py"
  - "../../../../backend/app/db/error_handling/error_translation.py"
  - "../../../../scripts/ci/sync-openapi.sh"
  - "../../../../frontend/apps/studio-app/src/api/generated/schema.ts"
change_triggers:
  - "../../../../backend/app/api/v1/"
  - "../../../../backend/app/schema/api/"
  - "../../../../backend/app/openapi/"
  - "../../../../backend/app/core/errors.py"
  - "../../../../backend/app/db/error_handling/"
  - "../../../../scripts/ci/check-openapi-contracts.sh"
related_docs: ["Backend knowledge", "Backend feature slices", "Frontend implementation", "Testing workflow", "Generated files"]
---

# Backend API contracts and errors

FlowForm keeps runtime HTTP behavior, typed schemas, generated API description,
and frontend consumption connected without making any one generated artifact
the runtime framework. Flask routes execute requests, Pydantic validates data,
OpenAPI metadata describes the public surface, and generated TypeScript carries
that surface into Studio.

```text
Flask route + Pydantic schema
             |
       +-----+-----+
       |           |
       v           v
runtime request   OpenAPI 3.1 document
and response            |
       |                v
       |        generated TypeScript
       +----------------+
```

## Runtime request and response boundary

Versioned Flask blueprints group account, Studio, respondent, and system
routes. A typical route:

1. declares its authentication and authorization decorators;
2. parses a JSON object or query parameters through a Pydantic API schema;
3. resolves request-scoped database sessions and actor context;
4. delegates the use case to a service or domain policy; and
5. validates and serializes the response through a response schema.

API schemas are separate from SQLAlchemy ORM models. That separation prevents a
database mapping from becoming the public wire contract by accident and lets
routes expose only the fields appropriate to the caller.

Request validation converts Pydantic failures into one application-level
validation error. Response validation failures are treated as server defects:
the detail is logged, while the caller receives the generic internal-error
shape rather than schema internals.

## OpenAPI and generated clients

The `openapi_route` decorator records summary, path, method, request/query and
response models, status, authentication mode, and available RBAC metadata. It
is documentation-only: it does not parse requests, enforce authorization, or
format responses. The spec builder combines this registry with Flask's route
map and Pydantic JSON schemas to generate OpenAPI 3.1.1.

The OpenAPI HTTP endpoint and CLI are registered only in development and test
applications. The checked-in `backend/openapi.yaml` is regenerated through the
repository contract workflow, which also generates Studio's TypeScript schema,
RBAC metadata, and shared schema types. CI checks export drift, generated-file
drift, and OpenAPI linting. Generated files are outputs; behavior changes start
in routes, schemas, authorization metadata, or the spec builder.

This establishes contract consistency with the checked-in source. It does not
prove backward compatibility, client rollout order, or that a deployed client
and server use the same revision.

## Normalized error model

JSON API failures share one top-level shape:

```json
{
  "code": "MACHINE_READABLE_CODE",
  "message": "Human-readable description.",
  "details": {}
}
```

`details` is omitted when empty. The global error boundary maps:

| Failure source | API treatment |
| --- | --- |
| Domain, authentication, authorization, or rate-limit `AppError` | Uses the error's declared status, code, message, details, and safe response headers. |
| Invalid request schema | `422 VALIDATION_ERROR` with normalized field, type, and message entries. |
| Invalid server response schema | Logged server defect and generic `500 INTERNAL_SERVER_ERROR`. |
| Werkzeug HTTP exception | Matching HTTP status with an `HTTP_<status>` code. |
| Unexpected exception | Logged failure and generic `500 INTERNAL_SERVER_ERROR`. |

Database integrity failures have an earlier translation boundary. Named
constraints and selected driver errors are mapped to domain-appropriate
application errors around flush or commit. A raw SQLAlchemy integrity error
that escapes those helpers is treated as an unhandled server defect, preventing
database diagnostics from becoming a public contract.

## Contract-change implications

A public API change may affect more than its route. Check the request/response
schema, service behavior, error vocabulary, authentication/RBAC metadata,
OpenAPI output, generated TypeScript, and frontend caller together. Database
schema changes remain independently owned by the migration and persisted-schema
workflow.

## Related documents

- [[backend-index|Backend knowledge]]
- [[feature-slices|Backend feature slices]]
- [[frontend-index|Frontend implementation]]
- [[testing|Testing workflow]]
- [[generated-files|Generated files]]
