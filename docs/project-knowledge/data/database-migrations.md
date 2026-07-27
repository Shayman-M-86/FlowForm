---
title: Database migrations
aliases: ["Database migrations"]
document_type: workflow
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [backend]
related_code:
  - "../../../infra/database/init/"
  - "../../../infra/database/flowform_*_mock_data.sql"
  - "../../../backend/app/schema/orm/"
  - "../../../backend/app/db/error_handling/"
  - "../../../backend/scripts/run-tests.sh"
related_docs:
  - "Data knowledge"
  - "Responses and encryption"
  - "Configuration implementation"
---

# Database migrations

This page describes the repository's current schema-change path. The checked-in
database assets create empty PostgreSQL databases from maintained SQL schemas
and initialization templates. They are suitable for disposable development and
test environments; they do not establish an incremental upgrade, downgrade, or
rollback procedure for a database that contains retained data.

## Change boundary

A database change can affect the core schema, response schema, role and grant
templates, SQLAlchemy mappings, API models, domain services, error translation,
and mock data. The core and response schemas remain separate: response data
should not gain direct core identifiers or database-level foreign keys merely
to simplify an application query. Constraint names are also part of the
application contract where integrity-error handling maps them to domain errors.

## Disposable-database workflow

1. Update the appropriate schema under `infra/database/init/schema/` and the
   initialization templates when roles, schemas, or grants change.
2. Align ORM models and the service/API contract that depends on the changed
   structure; update mock data where fixture rows no longer satisfy constraints.
3. Add or adjust tests for supported behaviour and important database
   enforcement.
4. Recreate a disposable database so PostgreSQL initialization runs from an
   empty data directory, then run the backend test workflow. The repository's
standard clean rebuild entry point is `bash backend/scripts/run-tests.sh
--clean-rebuild --ai`.

```text
schema SQL + grants/templates
             |
             +--> ORM / API / service alignment
             |
             +--> fixture and test updates
             |
             v
      recreate empty database
             |
             v
      initialization executes
             |
             v
          test suite

retained data --> separate designed and authorized migration path
```

Editing an initialization schema and restarting an existing PostgreSQL volume
does not apply the change: the official entrypoint initializes only an empty
data directory. A retained environment therefore needs a separately designed,
tested, and authorized operational migration plan before its schema changes.

## Related documents

- [[data-index|Data knowledge]]
- [[responses-and-encryption|Responses and encryption]]
- [[configuration|Configuration implementation]]
