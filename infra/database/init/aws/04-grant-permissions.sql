-- FlowForm AWS/RDS runtime grants for one database.
--
-- The runner invokes this once per database with :app_schema and :app_user
-- set, connected to the target database as flowform_admin.
--
-- These mirror the shared container templates. The runtime identities get CRUD
-- on data and nothing structural: no CREATE, no extension management, no role
-- management, no blanket ALL PRIVILEGES.
--
-- Re-runnable: grants are idempotent.

\set ON_ERROR_STOP on

GRANT USAGE ON SCHEMA :"app_schema" TO :"app_user";

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA :"app_schema"
TO :"app_user";

GRANT USAGE, SELECT, UPDATE
ON ALL SEQUENCES IN SCHEMA :"app_schema"
TO :"app_user";

-- Default privileges are recorded FOR ROLE flowform_owner because the schema
-- load creates objects under that role. This only has effect because the
-- objects are genuinely owner-owned; see the ownership assertion in the load
-- step.
ALTER DEFAULT PRIVILEGES FOR ROLE flowform_owner IN SCHEMA :"app_schema"
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
TO :"app_user";

ALTER DEFAULT PRIVILEGES FOR ROLE flowform_owner IN SCHEMA :"app_schema"
GRANT USAGE, SELECT, UPDATE ON SEQUENCES
TO :"app_user";

ALTER ROLE :"app_user" SET search_path = :"app_schema";
