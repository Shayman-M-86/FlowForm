# Postgres Init Bootstrap

This folder contains the database bootstrap logic that runs automatically on first container startup.

## What it does

- Creates the core and response databases
- Creates application roles (users)
- Loads schema files
- Applies permissions and access control

## How it works

Docker mounts this folder to `/docker-entrypoint-initdb.d`.

On first initialization of the Postgres data volume:

1. The shell script renders SQL templates using environment variables
2. The rendered SQL is executed in order
3. Databases, roles, schemas, and permissions are created

## Notes

- Runs only on first boot (when the volume is empty)
- Requires `.env` variables to be set correctly
- Designed for local development and reproducible setup

## Required Environment Variables

The following variables must be defined (typically via `.env` and passed through Docker Compose):

```env
POSTGRES_USER=flowform
POSTGRES_PASSWORD=your_admin_password
POSTGRES_DB=postgres

FLOWFORM_CORE_DB=flowform_core
FLOWFORM_RESPONSE_DB=flowform_response

FLOWFORM_CORE_APP_USER=flowform_core_app
FLOWFORM_CORE_APP_PASSWORD=core_password_here

FLOWFORM_RESPONSE_APP_USER=flowform_response_app
FLOWFORM_RESPONSE_APP_PASSWORD=response_password_here

FLOWFORM_CORE_SCHEMA_FILE=/docker-entrypoint-initdb.d/schema/flowform_core_db_schema_tightened.sql
FLOWFORM_RESPONSE_SCHEMA_FILE=/docker-entrypoint-initdb.d/schema/flowform_response_db_schema_tightened.sql
```

## Example (templates + variables)

**Template snippet (01-roles.sql):**

```sql
CREATE ROLE ${FLOWFORM_CORE_APP_USER} LOGIN PASSWORD '${FLOWFORM_CORE_APP_PASSWORD}';
```

**.env variables:**

```env
FLOWFORM_CORE_APP_USER=flowform_core_app
FLOWFORM_CORE_APP_PASSWORD=core_password_here
```

**Rendered SQL (executed by psql):**

```sql
CREATE ROLE flowform_core_app LOGIN PASSWORD 'core_password_here';
```
