---
title: Backend knowledge
aliases: ["Backend knowledge"]
document_type: overview
status: verified
authority: canonical
verified_evidence_digest: sha256:8dc49a5dd87e98f4fd2e292b82c715e3d64743e182838a00c52fbfeab3ba3617
last_edited: 2026-08-04
tags: [backend]
related_code:
  - "../../../backend/app/core/factory.py"
  - "../../../backend/app/api/v1/__init__.py"
  - "../../../backend/app/db/manager.py"
change_triggers:
  - "../../../backend/app/"
  - "../../../backend/tests/"
related_docs:
  - "Data flows"
  - "Backend implementation documentation"
  - "Backend runtime composition"
  - "Backend API contracts and errors"
  - "Identity and authentication"
  - "Responses and encryption"
  - "Telemetry and health"
---

# Backend knowledge

This branch describes the Flask backend's domain responsibilities and the
implementation patterns used to change it. The backend exposes account,
Studio, respondent, and system APIs; coordinates authentication,
authorization, domain workflows, and external integrations; and keeps core
project metadata separate from encrypted response persistence.

The domain pages explain the lifecycle and ownership of projects, surveys,
respondent access, and submission attempts. The implementation branch explains
how those responsibilities are organised in code. Infrastructure configuration,
identity, cryptography, and generated API references are owned by their
respective branches; this branch links to them instead of duplicating their
details.

```text
Studio / respondent / system clients
                 |
                 v
        routes + API schemas
                 |
                 v
       authorization + services
             /          \
            v            v
       core metadata   response coordination
            |            |
            v            v
       Core store     Response store
```

## Architectural responsibilities

The backend uses a layered request path rather than treating Flask route
handlers as the application boundary in full:

| Layer | Primary responsibility |
| --- | --- |
| Blueprints and routes | HTTP paths, authentication decorators, request parsing, response status, and delegation |
| Pydantic API schemas | Request and response shapes independent of ORM models |
| Services | Use-case orchestration, permission-aware work, transactions, encryption, and cross-repository workflows |
| Domain policy | Reusable rules, guards, permissions, and answer/version validation without HTTP concerns |
| Repositories | Named SQLAlchemy queries and persistence mutations against an explicit session |
| ORM and SQL schemas | Persisted shape, relationships, constraints, and store ownership |

This is an observed ownership model supported by repository guidance and tests;
it is not an automatically enforced dependency graph. A feature can omit a
layer when that layer would add no responsibility, but routes should not own
business queries and repositories should not decide transport behavior.

## Cross-cutting capabilities

| Capability | Backend boundary | Canonical detail |
| --- | --- | --- |
| Operator identity | Auth0 bearer-token verification followed by local user resolution | [[identity-and-authentication|Identity and authentication]] |
| Project and survey authorization | Project membership, project roles, survey roles, and named permissions | [[projects-and-access|Projects and access]] |
| Respondent continuity | Link policy, subject resolution, recognition tokens, and resume credentials | [[links-and-subjects|Links and subjects]] and [[submissions|Submissions]] |
| Privacy-aware response storage | Opaque cross-store locators, wrapped keys, and encrypted current answers | [[responses-and-encryption|Responses and encryption]] |
| API integration | Pydantic runtime boundaries, OpenAPI generation, normalized errors, and generated frontend contracts | [[api-contracts-and-errors|Backend API contracts and errors]] |
| Runtime composition | Typed settings, extensions, per-request sessions, worker lifecycle, and external clients | [[backend-runtime-composition|Backend runtime composition]] |
| Operational signals | Health checks, structured request logs, request correlation, and traces | [[telemetry-and-health|Telemetry and health]] |

Core and response stores are independent persistence boundaries. Consequently,
workflows that span them need explicit sequencing, compensation, or
reconciliation rather than a distributed database transaction. The backend can
open both stores and access decryption material for authorized work, so the
split is data minimisation and linkage control—not a security boundary against
a compromised backend process.

Pages remain draft until their claims are checked against implementation
evidence; code, schemas, configuration, and tests remain authoritative.

## Topics

- [[data-flows|Data flows]] traces the principal cross-boundary workflows.
- [[projects-and-access|Projects and access]], [[surveys-and-versioning|Surveys and versioning]],
  [[links-and-subjects|Links and subjects]], and [[submissions|Submissions]]
  describe the main backend domains.
- [[implementation-index|Backend implementation documentation]]
  describes code-level patterns.
- [[backend-runtime-composition|Backend runtime composition]] describes
  process startup, extensions, database sessions, and worker lifecycle.
- [[api-contracts-and-errors|Backend API contracts and errors]] describes the
  typed HTTP boundary and generated client-contract path.

## Related documents

- [[data-flows|Data flows]]
- [[implementation-index|Backend implementation documentation]]
- [[identity-and-authentication|Identity and authentication]]
- [[responses-and-encryption|Responses and encryption]]
- [[telemetry-and-health|Telemetry and health]]
