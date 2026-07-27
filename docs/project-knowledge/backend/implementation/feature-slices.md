---
title: Backend feature slices
aliases: ["Backend feature slices"]
document_type: implementation
status: verified
authority: canonical
verified_evidence_digest: sha256:1341271d646459f6a9958d1dec6f3aef1a07519701cfc2c26e4668795935568a
last_edited: 2026-07-27
tags: [backend]
related_code:
  - "../../../../backend/app/api/v1/"
  - "../../../../backend/app/schema/api/"
  - "../../../../backend/app/services/"
  - "../../../../backend/app/repositories/"
  - "../../../../backend/openapi.yaml"
  - "../../../../scripts/ci/sync-openapi.sh"
related_docs:
  - "Backend implementation documentation"
  - "Backend code organization"
  - "Testing workflow"
---

# Backend feature slices

This draft gives a repeatable boundary-oriented shape for a backend feature:

```text
API schema -> route -> service/domain policy -> repository -> ORM or SQL schema
```

Start by locating the owning blueprint and the relevant persistence store.
Define the request/response contract, keep the route thin, introduce or extend
a service when the operation coordinates policy, permissions, encryption, or
multiple repositories, and put database work behind focused repository methods.
If the public contract changes, regenerate the OpenAPI-derived artifacts rather
than editing generated files.

Tests should match the changed boundary: route/contract behaviour for HTTP work,
unit coverage for policy, integration coverage for persistence, and regenerated
contract checks for API changes. Exact commands and current test ownership remain
subject to the testing/reference branch.

## Related documents

- [[implementation-index|Backend implementation documentation]]
- [[code-organization|Backend code organization]]
- [[backend-index|Backend knowledge]]
