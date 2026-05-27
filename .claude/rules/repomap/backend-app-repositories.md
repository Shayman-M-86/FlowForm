---
paths: backend/app/repositories/**
---

# backend/app/repositories/

_Last updated: 2026-05-27 by /repomap_

Thin data-access layer containing one module per entity (e.g., surveys_repo.py, submissions_repo.py, users_repo.py, roles_repo.py). Each module exposes plain functions that accept a SQLAlchemy Session and return ORM objects — there are no repository classes, only free functions. submissions_repo.py is representative: it builds SQLAlchemy select() queries with filters, pagination, and selectinload() for eager-loading relationships, then returns typed tuples of results and totals. The dual-database (core/response) architecture is reflected in separate response_stores_repo.py modules.
