\set ON_ERROR_STOP on

-- Create the core database if it does not already exist.
SELECT 'CREATE DATABASE ${FF_PGDB_CORE__DB_NAME}'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = '${FF_PGDB_CORE__DB_NAME}'
)\gexec

-- Create the response database if it does not already exist.
SELECT 'CREATE DATABASE ${FF_PGDB_RESPONSE__DB_NAME}'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = '${FF_PGDB_RESPONSE__DB_NAME}'
)\gexec