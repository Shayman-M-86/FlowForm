\set ON_ERROR_STOP on

-- Create the shared owner role.
-- This role owns schemas/objects but does not log in directly.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_owner') THEN
        CREATE ROLE flowform_owner NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DATABASE_CORE_APP_USER}') THEN
        CREATE ROLE ${DATABASE_CORE_APP_USER}
        LOGIN
        PASSWORD '${DATABASE_CORE_APP_PASSWORD}';
    END IF;
END
$$;

ALTER ROLE ${DATABASE_CORE_APP_USER}
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

GRANT CONNECT ON DATABASE ${DATABASE_CORE_NAME}
TO ${DATABASE_CORE_APP_USER};
