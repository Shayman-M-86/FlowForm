---
paths: backend/app/schema/**
---

# backend/app/schema/

Schema code: shapes backend accept, return, persist.

Keep halves distinct:

- `api/` holds Pydantic request/response contracts.
- `orm/` holds SQLAlchemy mappings.
- `enums.py` and `api/limits.py` keep shared contract values explicit.

DB SQL files = migration source of truth. ORM metadata: model what app needs for relationships, flush behavior, local validation. Not second migration system.

SQL schema files live in `infra/postgres/init/schema/`.

No import ORM models into Pydantic schemas. Keep API contracts stable even when persistence details move.
