# Postgres Init Bootstrap

This folder contains the database bootstrap logic that runs automatically on first container startup.

## Template Layout

The SQL templates are organized by responsibility:

- `templates/shared` contains SQL used only when bootstrapping both databases in one cluster
- `templates/core` contains SQL specific to the core database container
- `templates/response` contains SQL specific to the response database container

## What it does

- In `all` mode, creates the core and response databases in a single cluster
- In `core` or `response` mode, bootstraps one database per Postgres container
- Creates application roles (users) from the init folder during first boot
- Loads schema files
- Applies permissions and access control

## How it works

Docker mounts this folder to `/docker-entrypoint-initdb.d`.

On first initialization of the Postgres data volume:

1. The shell script renders SQL templates using environment variables
2. The script chooses `core`, `response`, or `all` bootstrap mode using `FF_PGDB_INIT__TARGET`
3. The rendered SQL is executed in order
4. Roles, schemas, and permissions are created inside the target Postgres container

## Notes

- Runs only on first boot (when the volume is empty)
- Requires `.env` variables to be set correctly
- Designed for local development and reproducible setup
- Relative schema paths are supported and resolved from `/docker-entrypoint-initdb.d`

## Required Environment Variables

The following variables must be defined (typically via `.env` and passed through Docker Compose):

```env
FF_PGDB_INIT__USER=flowform
FF_PGDB_INIT__DB=postgres

FF_PGDB_INIT__TARGET=core

FF_PGDB_CORE_COMPOSE__HOST=postgres-core
FF_PGDB_CORE_COMPOSE__PORT=5432
FF_PGDB_CORE_COMPOSE__PUBLISHED_PORT=5432

FF_PGDB_RESPONSE_COMPOSE__HOST=postgres-response
FF_PGDB_RESPONSE_COMPOSE__PORT=5432
FF_PGDB_RESPONSE_COMPOSE__PUBLISHED_PORT=5433

FF_PGDB_CORE__DB_NAME=flowform_core
FF_PGDB_RESPONSE__DB_NAME=flowform_response

FF_PGDB_CORE__APP_USER=flowform_core_app
FF_PGDB_CORE__APP_PASSWORD=core_password_here

FF_PGDB_RESPONSE__APP_USER=flowform_response_app
FF_PGDB_RESPONSE__APP_PASSWORD=response_password_here

FF_PGDB_CORE__SCHEMA_FILE=schema/flowform_core_db_schema_tightened.sql
FF_PGDB_RESPONSE__SCHEMA_FILE=schema/flowform_response_db_schema_tightened.sql
```

## Bootstrap Modes

- `FF_PGDB_INIT__TARGET=core`: creates the core app user, schema, and permissions in the core Postgres container
- `FF_PGDB_INIT__TARGET=response`: creates the response app user, schema, and permissions in the response Postgres container
- `FF_PGDB_INIT__TARGET=all`: preserves the previous single-cluster bootstrap behavior

## Example (templates + variables)

**Template snippet (`templates/shared/01-create-roles.sql`):**

```sql
CREATE ROLE ${FF_PGDB_CORE__APP_USER} LOGIN PASSWORD '${FF_PGDB_CORE__APP_PASSWORD}';
```

**.env variables:**

```env
FF_PGDB_CORE__APP_USER=flowform_core_app
FF_PGDB_CORE__APP_PASSWORD=core_password_here
```

**Rendered SQL (executed by psql):**

```sql
CREATE ROLE flowform_core_app LOGIN PASSWORD 'core_password_here';
```
