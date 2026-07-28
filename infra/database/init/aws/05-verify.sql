-- FlowForm AWS/RDS post-bootstrap verification.
--
-- Runs as flowform_admin against the maintenance database. Proves the role and
-- isolation invariants rather than assuming the earlier steps had the intended
-- effect. Fails loudly on the first violation.
--
-- Connection-level isolation (each app role reaching only its own database) is
-- checked by the runner, which can open real connections; catalogue inspection
-- alone cannot prove it.

\set ON_ERROR_STOP on

DO $$
DECLARE
    failures TEXT := '';
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_owner' AND rolcanlogin) THEN
        failures := failures || E'\n- flowform_owner must be NOLOGIN';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_owner') THEN
        failures := failures || E'\n- flowform_owner is missing';
    END IF;

    -- Runtime identities must be low privilege.
    IF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname IN ('flowform_core_app', 'flowform_response_app')
          AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
    ) THEN
        failures := failures || E'\n- a runtime identity holds an elevated attribute';
    END IF;

    -- IAM authentication must be in force for both runtime identities.
    IF EXISTS (
        SELECT 1 FROM unnest(ARRAY['flowform_core_app', 'flowform_response_app']) AS r(name)
        WHERE NOT pg_has_role(r.name, 'rds_iam', 'MEMBER')
    ) THEN
        failures := failures || E'\n- a runtime identity is not granted rds_iam';
    END IF;

    -- Under IAM authentication no runtime identity should carry a stored
    -- password; one would be an alternative credential outside the token path.
    IF EXISTS (
        SELECT 1 FROM pg_authid
        WHERE rolname IN ('flowform_core_app', 'flowform_response_app')
          AND rolpassword IS NOT NULL
    ) THEN
        failures := failures || E'\n- a runtime identity has a stored password';
    END IF;

    -- PUBLIC must not hold CONNECT on either application database.
    IF has_database_privilege('public', 'flowform_core', 'CONNECT')
       OR has_database_privilege('public', 'flowform_response', 'CONNECT') THEN
        failures := failures || E'\n- PUBLIC still holds CONNECT on an application database';
    END IF;

    -- Each runtime identity must reach exactly one database.
    IF NOT has_database_privilege('flowform_core_app', 'flowform_core', 'CONNECT') THEN
        failures := failures || E'\n- flowform_core_app cannot connect to flowform_core';
    END IF;
    IF has_database_privilege('flowform_core_app', 'flowform_response', 'CONNECT') THEN
        failures := failures || E'\n- flowform_core_app can reach the response database';
    END IF;
    IF NOT has_database_privilege('flowform_response_app', 'flowform_response', 'CONNECT') THEN
        failures := failures || E'\n- flowform_response_app cannot connect to flowform_response';
    END IF;
    IF has_database_privilege('flowform_response_app', 'flowform_core', 'CONNECT') THEN
        failures := failures || E'\n- flowform_response_app can reach the core database';
    END IF;

    IF failures <> '' THEN
        RAISE EXCEPTION 'FlowForm database verification failed:%', failures;
    END IF;
END
$$;
