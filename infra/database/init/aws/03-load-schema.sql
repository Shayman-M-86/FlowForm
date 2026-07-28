-- FlowForm AWS/RDS schema load for one database.
--
-- The runner invokes this once per database with :db_name, :app_schema, and
-- :schema_file already set, connected to the target database as
-- flowform_admin.
--
-- Ordering here is deliberate and is the fix for an ownership defect in the
-- container entrypoint path: that path sets search_path, loads the schema,
-- then reasserts ownership of the *schema* only. Objects inside it stay owned
-- by the bootstrap administrator, and ALTER DEFAULT PRIVILEGES FOR ROLE
-- flowform_owner then silently applies to a role that owns nothing, so future
-- tables receive no grants. Creating the objects under SET ROLE avoids that
-- entirely rather than repairing it afterwards.

\set ON_ERROR_STOP on

-- pgcrypto must be installed by a privileged role, so it happens before the
-- SET ROLE below. flowform_owner cannot create extensions.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS :"app_schema" AUTHORIZATION flowform_owner;

-- The shared schema snapshots use unguarded CREATE TABLE, so loading them into
-- a populated schema fails. Skip the load when application objects already
-- exist: this step provisions an empty database and is not a migration path.
-- Changing an existing schema is the migration authority's job, not this
-- script's.
SELECT count(*) = 0 AS schema_is_empty
FROM pg_tables
WHERE schemaname = :'app_schema'
\gset

\if :schema_is_empty
\else
\echo 'application objects already exist; skipping schema load'
\quit
\endif

-- Lock down the default public schema and the application schema. Explicit
-- grants are applied by the grant step, not inherited from PUBLIC.
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA :"app_schema" FROM PUBLIC;

-- Create every application object as the owner, not as the administrator.
SET ROLE flowform_owner;

-- Unqualified CREATE lands in the application schema, but public stays on the
-- path so pgcrypto's functions (gen_random_uuid, gen_random_bytes) resolve
-- while the schema file runs. Dropping public here fails at the first column
-- default that calls one.
SET search_path TO :"app_schema", public;

\i :schema_file

RESET ROLE;

-- Ownership should already be correct; assert rather than assume. psql
-- variables do not interpolate inside a dollar-quoted body, so the count is
-- taken here and checked with \if rather than inside a DO block.
--
-- This guards the fresh-load path only: the skip above returns earlier when
-- objects already exist, so it will not detect or repair bad ownership in an
-- already-populated database. That is the migration authority's concern.
SELECT count(*) = 0 AS ownership_ok
FROM pg_tables
WHERE schemaname = :'app_schema'
  AND tableowner <> 'flowform_owner'
\gset

\if :ownership_ok
\else
\echo 'ERROR: schema load left tables not owned by flowform_owner'
\quit 1
\endif
