---
name: integrity-rules-and-sql-constraints
description: Use when adding, renaming, or reviewing FlowForm SQL constraints and integrity-rule mappings.
user-invocable: false
paths:
  - "infra/postgres/init/schema/**/*.sql"
  - "backend/app/db/error_handling/integrity_rules.py"
  - "backend/app/schema/orm/**/*.py"
  - "backend/scripts/check_integrity_rule_constraints.py"
  - "backend/scripts/check-integrity-rule-constraints.sh"
---

# Integrity Rules And SQL Constraints

Use when constraints or `integrity_rules.py` change.

## Rules

- SQL schema is runtime truth:
  `infra/postgres/init/schema/flowform_{core,response}_db_schema_v4.sql`.
- Define CHECKs, ordinary UNIQUEs, and business constraints in SQL.
- Do not mirror CHECKs or ordinary UNIQUEs in SQLAlchemy.
- Put constraints in SQLAlchemy only when ORM needs them:
  foreign keys, relationship joins, and composite UNIQUEs targeted by composite FKs.
- Keep ORM column type/nullability/default aligned with SQL.
- Constraint names are API behavior: `integrity_rules.py` matches exact Postgres names.
- Prefer explicit `ck_*`, `fk_*`, `uq_*`, `pk_*` names.

## Workflow

1. Add/change SQL constraint first.
2. Add upstream validation if client can trigger it:
   `schema/api/requests`, `domain`, then `services`.
3. Add integrity rule only when DB violation should become deliberate API error:
   race/concurrency or cross-table -> `409`; server invariant -> `500`.
4. If intentionally unmapped, keep rationale clear.
5. Pass right ORM context to `flush_with_err_handle` / `commit_with_err_handle`.
6. Update mock data and tests.
7. Run checker.

## Integrity Checker

```bash
bash backend/scripts/check-integrity-rule-constraints.sh
bash backend/scripts/check-integrity-rule-constraints.sh --details
bash backend/scripts/check-integrity-rule-constraints.sh --show-advisory
bash backend/scripts/check-integrity-rule-constraints.sh --verbose
```

Fail means dead rule, wrong matcher type, or likely `UNHANDLED_DB_INTEGRITY_ERROR`.
