\set ON_ERROR_STOP on

-- Create the shared owner role.
-- This role owns schemas/objects but does not log in directly.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_owner') THEN
        CREATE ROLE flowform_owner NOLOGIN;
    END IF;

    -- Runtime role for the core database.
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DATABASE_CORE_APP_USER}') THEN
        CREATE ROLE ${DATABASE_CORE_APP_USER}
        LOGIN
        PASSWORD '${DATABASE_CORE_APP_PASSWORD}';
    END IF;

    -- Runtime role for the response database.
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DATABASE_RESPONSE_APP_USER}') THEN
        CREATE ROLE ${DATABASE_RESPONSE_APP_USER}
        LOGIN
        PASSWORD '${DATABASE_RESPONSE_APP_PASSWORD}';
    END IF;
END
$$;

-- Explicitly keep runtime roles low-privilege.
ALTER ROLE ${DATABASE_CORE_APP_USER}
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

ALTER ROLE ${DATABASE_RESPONSE_APP_USER}
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

-- Allow each app role to connect only to its database.
GRANT CONNECT ON DATABASE ${DATABASE_CORE_NAME}
TO ${DATABASE_CORE_APP_USER};

GRANT CONNECT ON DATABASE ${DATABASE_RESPONSE_NAME}
TO ${DATABASE_RESPONSE_APP_USER};
