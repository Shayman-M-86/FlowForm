---
paths: backend/app/repositories/**
---

# backend/app/repositories/

Repositories are named persistence helpers. They hide SQLAlchemy query details
without owning business decisions.

Usual shape:

- `Session` in
- ORM row, scalar, list, or tuple out
- reads use `select()` and SQLAlchemy session helpers
- writes add, mutate, delete, and flush
- commits stay in services

Keep repositories local to one persistence concern. If a function starts
coordinating multiple stores, permissions, or workflows, move that behavior up
to a service.
