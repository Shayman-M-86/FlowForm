---
name: db-schema-change
description: Use when changing FlowForm's DB schema, including columns, constraints, tables, CHECKs, foreign keys, or schema-related migrations.
---

A schema change in FlowForm touches many layers. Before editing, walk this
checklist and identify which items apply. Not every change touches every
layer, but every change touches several. See
`backend/docs/db-schema-changes.md` for the full narrative and worked
examples.

## The Layers To Consider

1. **SQL schema** - `infra/postgres/init/schema/flowform_{core,response}_db_schema_v4.sql`. Runtime source of truth. Constraint names matter: `integrity_rules.py` keys off them exactly. Follow `sqlalchemy_constraint_naming_rules.md` in the same dir.

2. **ORM models** - `app/schema/orm/{core,response}/`. Column types/nullability/defaults match the SQL, but `__table_args__` is not a full mirror: the DB is built from SQL (never from ORM metadata), so keep only what SQLAlchemy needs - foreign keys and the composite UNIQUEs that composite FKs target. CHECKs and non-FK UNIQUEs live in SQL only. Core and response models never share base or relationship.

3. **Mock data** - `infra/postgres/flowform_{core,response}_mock_data.sql`. Every CHECK / FK / UNIQUE in the schema must be satisfied by the seed rows. New NOT NULL column: fill every existing `INSERT`. New CHECK: audit every existing row. Removed column: strip from `INSERT` and `setval(...)` lines.

4. **Request schemas** - `app/schema/api/requests/`. Validate client-facing fields here for fast failure. Multi-field invariants use `@model_validator`. Size caps mirroring DB CHECKs should keep the constant cross-referenced.

5. **Response schemas** - `app/schema/api/responses/`. New column does not mean automatically exposed. Response-DB isolation: never expose real `user_id`.

6. **Domain rules** - `app/domain/`. State-aware checks, PATCH coherence, and state-machine transitions belong here. New error class goes in `app/domain/errors.py`: 409 for conflict, 422 for invalid payload structure, 500 for server-invariant violations.

7. **Services** - `app/services/`. Call the domain rule before the repo write. Use `model_fields_set` plus the loaded record for PATCH coherence. Pass the right contexts to `commit_with_err_handle`.

8. **Repositories** - `app/repositories/`. One DB only, named queries, honour `model_fields_set` on partial updates, use `flush_with_err_handle(contexts=[...])`.

9. **Integrity rules** - `app/db/error_handling/integrity_rules.py`. Decision: covered upstream means no rule, comment only; race-prone / cross-table / trigger means 409 rule; server-controlled field means 500 rule. Rule key must match the SQL constraint name exactly.

10. **Tests** - service-level path tests plus a raw-CHECK integration test, style: `tests/integration/core/test_surveys.py`, when the invariant is structural.

11. **OpenAPI** - examples auto-derive. Verify the new error class instantiates cleanly via `_instantiate_for_doc`; restart Flask to bust the spec cache.

## Cross-Cutting

- **Status codes** - 409 conflict, 422 structurally invalid payload, 500 server bug.
- **Defence in depth** - DB CHECK is the final guarantor; Pydantic/domain are for fast clean rejection. Usually want both.
- **Backwards compat** - adding nullable is safe; adding NOT NULL or new CHECK requires data audit; renames are breaking.

If the change would skip a layer that should have been touched, flag it before proceeding.
