---
title: Database migrations
aliases: ["Database migrations"]
document_type: workflow
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [backend]
related_code:
  - "../../../backend/scripts/run-tests.sh"
change_triggers:
  - "../../../infra/database/init/"
  - "../../../infra/database/flowform_*_mock_data.sql"
  - "../../../backend/app/schema/orm/"
  - "../../../backend/app/db/error_handling/"
related_docs:
  - "Data knowledge"
  - "Responses and encryption"
  - "Configuration and secrets"
---

# Database migrations

This page describes the repository's current schema-change path. The checked-in
database assets create a baseline PostgreSQL structure from maintained SQL
schemas. Development and test load it through initialization templates; the AWS
bootstrap loads the same baseline into empty application schemas on retained
RDS. Neither path establishes an incremental upgrade, downgrade, or rollback
procedure for a database that already contains application objects or data.

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

The AWS bootstrap is also a baseline-only path. It loads the authoritative
schema snapshots only when the target application schema is empty, rejects a
partial or unexpected table set, and verifies the completed baseline. Every
schema change after that point belongs to the future retained-data migration
path.

## Related documents

- [[data-index|Data knowledge]]
- [[responses-and-encryption|Responses and encryption]]
- [[configuration|Configuration and secrets]]
