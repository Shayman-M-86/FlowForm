---
paths: backend/app/**/*.py
---

# Backend Layers

HTTP at edge, persistence at bottom, workflow in middle.

- `api/routes/` translate HTTP into service calls.
- `schema/api/` describes request and response shapes.
- `services/` own use cases, workflows, and coordination.
- `repositories/` hide named database queries.
- `schema/orm/` defines SQLAlchemy tables and relationships.
- `db/` owns sessions, engines, and transaction helpers.

Routes thin. Models passive. HTTP/workflow/persistence mixing → move to owning layer.