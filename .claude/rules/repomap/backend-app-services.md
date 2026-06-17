---
paths: backend/app/services/**
---

# backend/app/services/

Services are the backend's use-case layer. They orchestrate domain rules,
repositories, and transactions without knowing HTTP details.

Good service code usually reads in this order:

- accept typed inputs, ids, sessions, and actor context
- load and persist through repositories
- call `app.domain` for policy and business decisions
- coordinate multi-step workflows in one place
- own commits and transaction boundaries
- return ORM rows or small result objects

Group services by use case. API-facing services can delegate to smaller core
services, but routes should not become the workflow layer.

Avoid services that are just renamed repositories, and avoid repositories that
quietly perform service-level coordination.
