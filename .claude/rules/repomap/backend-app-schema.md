---
paths: backend/app/schema/**
---

# backend/app/schema/

_Last verified: 2026-06-15_

Schema layer = API contracts + ORM mappings.

- `api/` -> Pydantic request/response models: `BaseModel`, `ConfigDict`,
  validators, `api/limits.py`, enum aliases from `schema/enums.py`.
- `orm/` -> SQLAlchemy models by DB: `core/` -> `CoreBase`, `response/` ->
  `ResponseBase`.
- `schema/enums.py` -> `Literal[...]` aliases mirror DB CHECK values. SQL enum
  change -> update here.
- `api/limits.py` -> OpenAPI/validation bounds; some from `PERMISSIONS`.

SQL files remain schema source of truth:

- `infra/postgres/init/schema/flowform_core_db_schema_v4.sql`
- `infra/postgres/init/schema/flowform_response_db_schema_v4.sql`

ORM metadata != migration source. Keep ORM constraints only when needed for
relationship/flush/local validation:

- composite FKs
- target composite UNIQUEs
- response locator/crypto `CheckConstraint`s
- mapping-critical rules

DB triggers own timestamp updates. `TimestampMixin` supplies `created_at` /
`updated_at`; no Python `onupdate`.

Keep `TEMP(rework)` legacy aliases until consumers move to current names:
`ResponseEnvelope`, `ResponseAnswer`, `SubmissionSession`, `ProjectSubject`,
etc.
