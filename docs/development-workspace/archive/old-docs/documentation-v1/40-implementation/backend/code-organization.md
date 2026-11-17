---
title: Backend code organization
aliases:
  - "Backend code organization"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: cd9bd50
tags: [backend]
related_code:
  - "../../../backend/app/core/factory.py"
  - "../../../backend/app/api/v1/"
  - "../../../backend/app/services/"
  - "../../../backend/app/domain/"
  - "../../../backend/app/repositories/"
  - "../../../backend/app/schema/"
  - "../../../backend/app/db/"
related_docs:
  - "Backend implementation guides"
  - "Backend implementation"
  - "Architecture principles"
---

# Backend code organization

Explains the current backend responsibility split and where to place new code.
It is a guide to the observed structure, not an import-lint rule.

## The normal request path

```text
HTTP route -> API request/response schema -> service or domain policy
          -> repository -> ORM mapping -> one database session
```

Routes live under `backend/app/api/v1/`. They are registered centrally in
`backend/app/api/v1/__init__.py`; the application factory calls that registrar
after initializing settings, extensions, and database sessions.

## Ownership map

| Location | Owns | Keep out of it |
| --- | --- | --- |
| `api/v1/` | Flask blueprints, HTTP parsing, decorators, schema use, HTTP responses | business workflows and direct persistence queries |
| `schema/api/` | Pydantic request and response contracts, shared API fields and limits | SQLAlchemy mappings or use-case orchestration |
| `services/` | use-case coordination, authorization-aware application work, transaction sequencing | route registration and generic ORM definitions |
| `domain/` | reusable domain policy that does not need to be an HTTP concern | Flask request/response handling |
| `repositories/` | query and persistence operations | API serialization and request validation |
| `schema/orm/core/` and `schema/orm/response/` | handwritten SQLAlchemy mappings for the respective stores | runtime schema creation |
| `db/` | session lifecycle, engine assembly, and database-error translation | feature-specific business rules |
| `core/` | application factory, typed settings, extension assembly, boot failures | feature implementations |

Core and response persistence are deliberately split. Keep repository and ORM
work for each store on its side of that boundary. A workflow touching both
stores needs explicit sequencing and recovery behaviour; it cannot rely on a
distributed transaction.

## File shapes to prefer

A small feature can stay in an existing feature module. When it has enough
surface area to warrant a package, the current layout supports this shape:

```text
backend/app/
├── api/v1/<area>/          # blueprint and HTTP-facing modules
├── schema/api/<area>/      # request/response contracts where useful
├── services/<area>.py      # one focused application service
├── repositories/<area>_repo.py
└── schema/orm/core/        # or schema/orm/response/ for its persistence model
```

The respondent submission flow uses deeper packages under
`services/public_submissions/`, and the administrative result flow similarly
uses `services/admin_results/`. Use a subpackage when its internal components
are a cohesive feature, not merely to mirror every directory in the request
path.

## Boundary checks before adding code

1. Put HTTP input/output shape in `schema/api/`, not in a route-local dict.
2. Put reusable persistence queries in a repository, not in a route.
3. Select the core or response database before creating a repository method.
4. Use a service when the operation coordinates authorization, several
   repositories, encryption, or transaction/recovery work.
5. Add a new top-level package only when it represents a durable responsibility;
   otherwise extend the closest existing feature module.

## Related documents

- [[40-implementation/backend/README|Backend implementation guides]]
- [[backend|Backend implementation]]
- [[architecture-principles|Architecture principles]]
