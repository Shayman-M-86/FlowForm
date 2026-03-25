\set ON_ERROR_STOP on

-- Create the shared owner role.
-- This role owns schemas/objects but does not log in directly.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_owner') THEN
        CREATE ROLE flowform_owner NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${FF_PGDB_CORE__APP_USER}') THEN
        CREATE ROLE ${FF_PGDB_CORE__APP_USER}
        LOGIN
        PASSWORD '${FF_PGDB_CORE__APP_PASSWORD}';
    END IF;
END
$$;

ALTER ROLE ${FF_PGDB_CORE__APP_USER}
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

GRANT CONNECT ON DATABASE ${FF_PGDB_CORE__DB_NAME}
TO ${FF_PGDB_CORE__APP_USER};