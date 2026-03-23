\set ON_ERROR_STOP on

-- Create the shared owner role.
-- This role owns schemas/objects but does not log in directly.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_owner') THEN
        CREATE ROLE flowform_owner NOLOGIN;
    END IF;

    -- Runtime role for the core database.
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${FLOWFORM_CORE_APP_USER}') THEN
        CREATE ROLE ${FLOWFORM_CORE_APP_USER}
        LOGIN
        PASSWORD '${FLOWFORM_CORE_APP_PASSWORD}';
    END IF;

    -- Runtime role for the response database.
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${FLOWFORM_RESPONSE_APP_USER}') THEN
        CREATE ROLE ${FLOWFORM_RESPONSE_APP_USER}
        LOGIN
        PASSWORD '${FLOWFORM_RESPONSE_APP_PASSWORD}';
    END IF;
END
$$;

-- Explicitly keep runtime roles low-privilege.
ALTER ROLE ${FLOWFORM_CORE_APP_USER}
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

ALTER ROLE ${FLOWFORM_RESPONSE_APP_USER}
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

-- Allow each app role to connect only to its database.
GRANT CONNECT ON DATABASE ${FLOWFORM_CORE_DB}
TO ${FLOWFORM_CORE_APP_USER};

GRANT CONNECT ON DATABASE ${FLOWFORM_RESPONSE_DB}
TO ${FLOWFORM_RESPONSE_APP_USER};