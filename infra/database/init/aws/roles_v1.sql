-- AWS/RDS roles packaged by DatabaseBootstrapStack.

DO $bootstrap$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_owner') THEN
        CREATE ROLE flowform_owner NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_migrator') THEN
        CREATE ROLE flowform_migrator LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_core_app') THEN
        CREATE ROLE flowform_core_app LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowform_response_app') THEN
        CREATE ROLE flowform_response_app LOGIN;
    END IF;
END
$bootstrap$;

ALTER ROLE flowform_owner
    NOLOGIN;

-- Reconcile these roles to passwordless IAM authentication on every run.
-- PostgreSQL masks password state in pg_roles, so PASSWORD NULL is enforced
-- directly here rather than inferred later from that public catalog view.
ALTER ROLE flowform_migrator
    LOGIN PASSWORD NULL;
ALTER ROLE flowform_core_app
    LOGIN PASSWORD NULL;
ALTER ROLE flowform_response_app
    LOGIN PASSWORD NULL;

GRANT flowform_owner TO flowform_admin WITH ADMIN OPTION;
GRANT flowform_owner TO flowform_migrator;
GRANT rds_iam TO flowform_migrator;
GRANT rds_iam TO flowform_core_app;
GRANT rds_iam TO flowform_response_app;
