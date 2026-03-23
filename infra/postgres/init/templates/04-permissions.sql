\set ON_ERROR_STOP on

-- =========================================================
-- Core database permissions
-- =========================================================

\connect ${FLOWFORM_CORE_DB}

-- Allow the core runtime role to use the core schema.
GRANT USAGE ON SCHEMA core_app TO ${FLOWFORM_CORE_APP_USER};

-- Grant runtime DML access on all current tables.
GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA core_app
TO ${FLOWFORM_CORE_APP_USER};

-- Grant access needed for BIGSERIAL / identity-backed inserts.
GRANT USAGE, SELECT, UPDATE
ON ALL SEQUENCES IN SCHEMA core_app
TO ${FLOWFORM_CORE_APP_USER};

-- Ensure future tables created by flowform_owner inherit the same grants.
ALTER DEFAULT PRIVILEGES FOR ROLE flowform_owner IN SCHEMA core_app
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
TO ${FLOWFORM_CORE_APP_USER};

-- Ensure future sequences created by flowform_owner inherit the same grants.
ALTER DEFAULT PRIVILEGES FOR ROLE flowform_owner IN SCHEMA core_app
GRANT USAGE, SELECT, UPDATE ON SEQUENCES
TO ${FLOWFORM_CORE_APP_USER};

-- Set the default schema for this role so app connections do not need
-- an explicit search_path in the connection string.
ALTER ROLE ${FLOWFORM_CORE_APP_USER} SET search_path = core_app;

-- =========================================================
-- Response database permissions
-- =========================================================

\connect ${FLOWFORM_RESPONSE_DB}

-- Allow the response runtime role to use the response schema.
GRANT USAGE ON SCHEMA response_app TO ${FLOWFORM_RESPONSE_APP_USER};

-- Grant runtime DML access on all current tables.
-- DELETE is intentionally omitted here for a more restrictive model.
GRANT SELECT, INSERT, UPDATE
ON ALL TABLES IN SCHEMA response_app
TO ${FLOWFORM_RESPONSE_APP_USER};

-- Grant sequence access needed for inserts.
GRANT USAGE, SELECT, UPDATE
ON ALL SEQUENCES IN SCHEMA response_app
TO ${FLOWFORM_RESPONSE_APP_USER};

-- Ensure future tables created by flowform_owner inherit the same grants.
ALTER DEFAULT PRIVILEGES FOR ROLE flowform_owner IN SCHEMA response_app
GRANT SELECT, INSERT, UPDATE ON TABLES
TO ${FLOWFORM_RESPONSE_APP_USER};

-- Ensure future sequences created by flowform_owner inherit the same grants.
ALTER DEFAULT PRIVILEGES FOR ROLE flowform_owner IN SCHEMA response_app
GRANT USAGE, SELECT, UPDATE ON SEQUENCES
TO ${FLOWFORM_RESPONSE_APP_USER};

-- Set the default schema for this role so app connections do not need
-- an explicit search_path in the connection string.
ALTER ROLE ${FLOWFORM_RESPONSE_APP_USER}
SET search_path = response_app;