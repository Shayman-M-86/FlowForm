-- AWS/RDS response database configuration packaged by DatabaseBootstrapStack.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

CREATE SCHEMA IF NOT EXISTS response_app AUTHORIZATION flowform_owner;
ALTER SCHEMA response_app OWNER TO flowform_owner;
REVOKE ALL ON SCHEMA response_app FROM PUBLIC;
REVOKE ALL ON SCHEMA response_app FROM flowform_core_app;
GRANT USAGE ON SCHEMA response_app TO flowform_response_app;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA response_app TO flowform_response_app;
GRANT USAGE, SELECT
    ON ALL SEQUENCES IN SCHEMA response_app TO flowform_response_app;
ALTER DEFAULT PRIVILEGES FOR ROLE flowform_owner IN SCHEMA response_app
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO flowform_response_app;
ALTER DEFAULT PRIVILEGES FOR ROLE flowform_owner IN SCHEMA response_app
    GRANT USAGE, SELECT ON SEQUENCES TO flowform_response_app;

ALTER ROLE flowform_response_app IN DATABASE flowform_response
    SET search_path = response_app, public;
ALTER ROLE flowform_migrator IN DATABASE flowform_response
    SET search_path = response_app, public;
