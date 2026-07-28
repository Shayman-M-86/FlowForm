-- FlowForm AWS/RDS role bootstrap.
--
-- Runs once per cluster as the RDS master identity (flowform_admin), which is
-- rds_superuser rather than a true superuser. Every statement here must be
-- valid for that privilege level.
--
-- Passwords are never interpolated into this file. The two runtime identities
-- authenticate with short-lived RDS IAM tokens, so they are created LOGIN with
-- no password at all and granted rds_iam.
--
-- Re-runnable: every statement is guarded or idempotent.

\set ON_ERROR_STOP on

-- Owner of all schemas and application objects. Never logs in; the migrator
-- assumes it explicitly with SET ROLE.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_owner') THEN
        CREATE ROLE flowform_owner NOLOGIN;
    END IF;
END
$$;

-- Runtime identities. No password is set: rds_iam makes the token the only
-- accepted credential, so these roles have no static secret to leak or rotate.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_core_app') THEN
        CREATE ROLE flowform_core_app LOGIN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_response_app') THEN
        CREATE ROLE flowform_response_app LOGIN;
    END IF;
END
$$;

-- Keep the runtime identities low privilege regardless of how they were made.
ALTER ROLE flowform_core_app
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

ALTER ROLE flowform_response_app
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

-- IAM authentication. This is the AWS-only statement that must never run
-- against the rehearsal or development clusters, which still use passwords.
-- The rds_iam role exists only on RDS.
GRANT rds_iam TO flowform_core_app;
GRANT rds_iam TO flowform_response_app;

-- flowform_admin must be a member of flowform_owner to set default privileges
-- on its behalf and to hand ownership over. rds_superuser is not a true
-- superuser, so this membership is required rather than implicit.
GRANT flowform_owner TO CURRENT_USER;
