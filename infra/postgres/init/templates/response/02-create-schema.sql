\set ON_ERROR_STOP on

-- Switch into the response database.
\connect ${FF_PGDB_RESPONSE__DB_NAME}

-- Create the dedicated application schema.
CREATE SCHEMA IF NOT EXISTS response_app AUTHORIZATION flowform_owner;

-- Lock down the default public schema.
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Lock down the application schema until explicit grants are applied later.
REVOKE ALL ON SCHEMA response_app FROM PUBLIC;

-- Make unqualified CREATE TABLE statements land in response_app.
SET search_path TO response_app;

-- Load the response schema file into the active search_path/schema.
\i ${FF_PGDB_RESPONSE__SCHEMA_FILE}

-- Reassert ownership on the schema.
ALTER SCHEMA response_app OWNER TO flowform_owner;