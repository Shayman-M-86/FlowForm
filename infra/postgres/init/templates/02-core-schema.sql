\set ON_ERROR_STOP on

-- Switch into the core database.
\connect ${FLOWFORM_CORE_DB}

-- Create the dedicated application schema.
CREATE SCHEMA IF NOT EXISTS core_app AUTHORIZATION flowform_owner;

-- Lock down the default public schema.
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Lock down the application schema until explicit grants are applied later.
REVOKE ALL ON SCHEMA core_app FROM PUBLIC;

-- Make unqualified CREATE TABLE statements land in core_app.
SET search_path TO core_app;

-- Load the core schema file into the active search_path/schema.
\i ${FLOWFORM_CORE_SCHEMA_FILE}

-- Reassert ownership on the schema.
ALTER SCHEMA core_app OWNER TO flowform_owner;