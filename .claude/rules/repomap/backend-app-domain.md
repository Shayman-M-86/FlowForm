---
paths: backend/app/domain/**
---

# backend/app/domain/

Domain = backend durable biz rules. Reusable from services, no HTTP knowledge.

Use for:

- policy checks and `ensure_*` guards
- typed domain errors
- shared permission/rule constants
- small pure decisions else duplicated

Prefer pure checks over DB work. Rule needs data → keep lookup narrow, let services coordinate full workflow.
