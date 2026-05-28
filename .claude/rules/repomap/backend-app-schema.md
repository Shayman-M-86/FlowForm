---
paths: backend/app/schema/**
---

# backend/app/schema/

_Last updated: 2026-05-27 by /repomap_

Holds two distinct schema sub-layers: `orm/` contains SQLAlchemy mapped model classes (split into `core/` and `response/` sub-packages mirroring the two databases), and `api/` contains request/response validation schemas with `enums.py` (Literal type aliases for all domain enums) and `limits.py` (field-length and count constants drawn from `PERMISSIONS`). ORM models use a shared `TimestampMixin` for `created_at`/`updated_at` columns maintained by DB triggers; the `Survey` model illustrates CHECK constraints and composite FKs enforced at the SQLAlchemy level.
