---
title: Backend code organization
aliases: ["Backend code organization"]
document_type: implementation
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [backend]
related_code:
  - "../../../../backend/app/core/factory.py"
change_triggers:
  - "../../../../backend/app/api/v1/"
  - "../../../../backend/app/services/"
  - "../../../../backend/app/domain/"
  - "../../../../backend/app/repositories/"
  - "../../../../backend/app/schema/"
  - "../../../../backend/app/db/"
related_docs:
  - "Backend implementation documentation"
  - "Backend knowledge"
---

# Backend code organization

This draft describes the observed responsibility split in `backend/app/`:
routes and API schemas handle transport; services and domain modules coordinate
use cases and policy; repositories and ORM models handle persistence; and core,
database, middleware, crypto, and extension packages provide shared runtime
boundaries.

A typical request progresses from an API route and request/response schema to a
service or domain policy, then a repository and the appropriate ORM/session.
Core and response persistence are separate. A feature that touches both needs
explicit sequencing and recovery behaviour rather than assuming one transaction.

```text
transport                    application                    persistence
+----------------+          +------------------+          +----------------+
| routes         |--------->| services         |--------->| repositories   |
| API schemas    |          | domain policy    |          | ORM models     |
+----------------+          +------------------+          +----------------+
        \                         |                              /
         +------------------------+-----------------------------+
                                  |
                    shared core / middleware / crypto
```

When extending the application, keep HTTP parsing out of services, persistence
queries out of routes, and feature policy out of shared assembly modules. Add a
new package only for a durable cohesive responsibility; otherwise extend the
nearest existing feature module.

## Related documents

- [[implementation-index|Backend implementation documentation]]
- [[feature-slices|Backend feature slices]]
- [[backend-index|Backend knowledge]]
