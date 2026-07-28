-- AWS/RDS core database configuration packaged by DatabaseBootstrapStack.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

CREATE SCHEMA IF NOT EXISTS core_app AUTHORIZATION flowform_owner;
ALTER SCHEMA core_app OWNER TO flowform_owner;
REVOKE ALL ON SCHEMA core_app FROM PUBLIC;
REVOKE ALL ON SCHEMA core_app FROM flowform_response_app;
GRANT USAGE ON SCHEMA core_app TO flowform_core_app;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA core_app TO flowform_core_app;
GRANT USAGE, SELECT
    ON ALL SEQUENCES IN SCHEMA core_app TO flowform_core_app;
ALTER DEFAULT PRIVILEGES FOR ROLE flowform_owner IN SCHEMA core_app
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO flowform_core_app;
ALTER DEFAULT PRIVILEGES FOR ROLE flowform_owner IN SCHEMA core_app
    GRANT USAGE, SELECT ON SEQUENCES TO flowform_core_app;

ALTER ROLE flowform_core_app IN DATABASE flowform_core
    SET search_path = core_app, public;
ALTER ROLE flowform_migrator IN DATABASE flowform_core
    SET search_path = core_app, public;
