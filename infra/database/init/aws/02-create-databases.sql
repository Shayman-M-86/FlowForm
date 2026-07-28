-- FlowForm AWS/RDS database creation and connection isolation.
--
-- Runs as flowform_admin against the maintenance database. Both logical
-- databases live in one cluster here, unlike local development's two separate
-- clusters, so PUBLIC CONNECT must be revoked explicitly: granting each app
-- role CONNECT on its own database does not remove PostgreSQL's default
-- PUBLIC grant on the other one.
--
-- Re-runnable: creation is guarded, revokes and grants are idempotent.

\set ON_ERROR_STOP on

SELECT 'CREATE DATABASE flowform_core OWNER flowform_owner'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'flowform_core'
)\gexec

SELECT 'CREATE DATABASE flowform_response OWNER flowform_owner'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'flowform_response'
)\gexec

-- Close the default before opening anything. Ordering matters: while PUBLIC
-- holds CONNECT, every role in the cluster can reach both databases.
REVOKE CONNECT ON DATABASE flowform_core FROM PUBLIC;
REVOKE CONNECT ON DATABASE flowform_response FROM PUBLIC;

-- Each runtime identity reaches exactly one database.
GRANT CONNECT ON DATABASE flowform_core TO flowform_core_app;
GRANT CONNECT ON DATABASE flowform_response TO flowform_response_app;
