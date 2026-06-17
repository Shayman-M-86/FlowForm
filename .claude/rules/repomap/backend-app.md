---
paths: backend/app/{*.py,core/**,db/**,logging/**,middleware/**,openapi/**,utils/**}
---

# backend/app/

Top-level app infrastructure: factory, config, extensions, middleware,
OpenAPI, logging, DB wiring, and small shared helpers.

`create_app` is the composition root. It wires the app together, but should not
own feature workflows.

Keep this area focused on application plumbing:

- app factory and config
- extension singletons and request lifecycle
- DB session helpers and transaction utilities
- middleware, URL converters, and rate limiting
- OpenAPI registration/export
- logging and audit hooks

Do not add feature-specific orchestration here. Put that in `services/`, with
local persistence hidden behind `repositories/`.
