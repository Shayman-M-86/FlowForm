\set ON_ERROR_STOP on

-- Create the core database if it does not already exist.
SELECT 'CREATE DATABASE ${DATABASE_CORE_NAME}'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = '${DATABASE_CORE_NAME}'
)\gexec

-- Create the response database if it does not already exist.
SELECT 'CREATE DATABASE ${DATABASE_RESPONSE_NAME}'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = '${DATABASE_RESPONSE_NAME}'
)\gexec
