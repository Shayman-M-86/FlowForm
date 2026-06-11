---
paths: backend/app/schema/**
---

# backend/app/schema/

_Last updated: 2026-05-27 by /repomap_

Holds two distinct schema sub-layers: `orm/` contains SQLAlchemy mapped model classes (split into `core/` and `response/` sub-packages mirroring the two databases), and `api/` contains request/response validation schemas with `enums.py` (Literal type aliases for all domain enums) and `limits.py` (field-length and count constants drawn from `PERMISSIONS`). ORM models use a shared `TimestampMixin` for `created_at`/`updated_at` columns maintained by DB triggers. The DB is built from the SQL schema files (never from ORM metadata), so `__table_args__` is not a full mirror of the SQL: it carries only the constraints SQLAlchemy needs — composite FKs and the composite UNIQUEs they target (the `Survey` and `SubmissionSession` models illustrate this) — while CHECKs and non-FK UNIQUEs live in the SQL schema only.
