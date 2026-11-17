---
title: Database migrations
aliases:
  - "Database migrations"
document_type: workflow
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [backend]
related_code:
  - "../../infra/database/init/"
  - "../../infra/database/flowform_*_mock_data.sql"
  - "../../backend/app/schema/orm/"
  - "../../backend/app/db/error_handling/"
  - "../../backend/scripts/run-tests.py"
related_docs:
  - "Backend implementation"
  - "Local infrastructure"
---

# Database migrations

Describes the database-schema change workflow that exists in the repository.
Despite the page title, FlowForm currently has no checked-in incremental
migration history or upgrade/downgrade runner. The implemented path initializes
empty PostgreSQL volumes from maintained SQL and validates changes by rebuilding
disposable databases.

## Trigger

Use this workflow when changing a core or response table, column, index,
constraint, database role, schema grant, or the ORM/API behaviour coupled to
that structure. A production database containing retained data requires a
separate migration and rollback plan that this repository does not yet provide.

## Preconditions

- PostgreSQL `17` runs through Docker Compose; uv and the backend test
  prerequisites from [[testing|Testing workflow]] are available.
- The gitignored `infra/env/dev/.env` interpolation file exists before using
  the local Compose commands below; the repository has no tracked template for
  this aggregate file at the current baseline.
- Core and response schemas remain separate. The response schema must not gain
  a foreign key or direct identifier back to core data.
- Any database whose volume will be removed is confirmed disposable. Back up
  retained data before designing or running an out-of-band migration.
- The canonical initialization SQL is
  `infra/database/init/schema/flowform_core_db_schema_v4.sql` and
  `flowform_response_db_schema_v4.sql`; ORM metadata does not create the runtime
  database.

## Ordered steps

1. Change the appropriate canonical SQL schema and, when role/bootstrap shape
   changes, the templates under `infra/database/init/templates/`.
2. Keep the corresponding SQLAlchemy model types, nullability, defaults,
   relationships, and composite constraints aligned. Update request/response
   schemas, domain rules, services, repositories, and named integrity-error
   translations only where the changed contract reaches them.
3. Update core or response mock SQL when new constraints or required columns
   affect the fixture rows.
4. Add tests for both the supported service path and structural database
   enforcement. Preserve exact constraint names consumed by
   `backend/app/db/error_handling/integrity_rules.py`.
5. Recreate the disposable test databases and run the suite:

   ```bash
   bash backend/scripts/run-tests.sh --clean-rebuild --ai
   ```

6. For a disposable development database, explicitly remove its volumes, start
   it again so the official PostgreSQL entrypoint reruns initialization, and
   reload mocks if wanted:

   ```bash
   docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml down -v
   docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml up -d --build
   scripts/dev/load-core-mock-data.sh
   scripts/dev/load-response-mock-data.sh
   ```

7. If the API contract changed, regenerate and review OpenAPI-derived frontend
   files with `bash scripts/ci/sync-openapi.sh`.

## Inputs and outputs

Inputs are the two maintained schema files, initialization templates, environment
and secret files, ORM/API changes, and optional mock data. On an empty volume,
`00-render-and-run.sh` renders credential-bearing SQL into container-local
`/tmp/flowform-init`, executes it with `ON_ERROR_STOP`, and creates application
roles, schemas, objects, and grants. Rebuilding deletes all data in the selected
Compose volumes; it does not produce an incremental migration artifact.

## Failure behaviour

PostgreSQL entrypoint initialization runs only when its data directory is empty.
Editing a schema file and restarting an existing volume changes nothing. Any
rendering or SQL error stops initialization, and fixture inserts use
`ON_ERROR_STOP` so a mismatch fails rather than partially seeding.

There is no implemented production ordering, online migration, backup/restore,
rollback, or cross-database release procedure. The CDK database stack is also a
placeholder. In addition, `backend/scripts/check_integrity_rule_constraints.py`
still resolves schema files under the removed `infra/postgres/...` path, so its
wrapper is not a valid verification command at this baseline.

## Verification commands

```bash
bash backend/scripts/run-tests.sh --clean-rebuild --ai
bash scripts/ci/check-openapi-contracts.sh
docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml ps
```

The first command is the meaningful schema proof because it creates fresh core
and response databases and exercises current tests. It does not prove that an
existing retained database can be upgraded safely.

## Related documents

- [[backend|Backend implementation]]
- [[local-infrastructure|Local infrastructure]]
