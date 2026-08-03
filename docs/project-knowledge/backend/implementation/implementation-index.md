---
title: Backend implementation documentation
aliases: ["Backend implementation documentation"]
document_type: overview
status: verified
authority: canonical
verified_evidence_digest: sha256:c744ece815ce6517988b5623fed0240b58abd7f008b89c70527a52f16022f4cf
last_edited: 2026-08-04
tags: [backend]
related_code: []
change_triggers:
  - "../../../../backend/app/"
  - "../../../../backend/tests/"
related_docs:
  - "Backend knowledge"
  - "Backend runtime composition"
  - "Backend API contracts and errors"
  - "Testing workflow"
---

# Backend implementation documentation

This branch provides construction-level guidance for changing the Flask
backend. Routes form the HTTP boundary; schemas define API and persistence
shapes; services coordinate use cases and authorization-aware work; repositories
encapsulate persistence; and core assembly owns settings, extensions, sessions,
and failure handling. This arrangement is an observed convention, not an
automatically enforced import rule.

The implementation documents focus on where a change belongs, how configuration
is introduced, and how a feature crosses route, schema, service, repository,
and contract boundaries. Product behaviour belongs in the parent backend domain
pages; generated API artifacts belong to reference/generated documentation.

```text
HTTP request
    |
 route + API schema
    |
 service / domain policy
    |
 repository
    |
 ORM / database session
    |
 core or response store
```

## Guides

- [[code-organization|Backend code organization]]
- [[feature-slices|Backend feature slices]]
- [[backend-configuration-patterns|Backend configuration patterns]]
- [[backend-runtime-composition|Backend runtime composition]]
- [[api-contracts-and-errors|Backend API contracts and errors]]

## Related documents

- [[backend-index|Backend knowledge]]
- [[code-organization|Backend code organization]]
- [[feature-slices|Backend feature slices]]
- [[backend-runtime-composition|Backend runtime composition]]
- [[api-contracts-and-errors|Backend API contracts and errors]]
- [[testing|Testing workflow]]
