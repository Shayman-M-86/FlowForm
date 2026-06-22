---
paths: backend/app/**/*.py
---

# Backend Layers

HTTP at edge, persistence at bottom, workflow in middle.

- `api/v1/` translates HTTP into service calls.
- `schema/api/` describes request and response shapes.
- `services/` own use cases, workflows, and transaction coordination.
- `domain/` owns reusable business rules and policy decisions.
- `repositories/` hide named database queries.
- `schema/orm/` defines SQLAlchemy tables and relationships.
- `db/` owns sessions, engines, and transaction helpers.

Routes thin. Domain rules pure when possible. Models passive.
HTTP/workflow/persistence mixing → move to owning layer.
