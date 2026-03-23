\set ON_ERROR_STOP on

-- Create the core database if it does not already exist.
SELECT 'CREATE DATABASE ${FLOWFORM_CORE_DB}'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = '${FLOWFORM_CORE_DB}'
)\gexec

-- Create the response database if it does not already exist.
SELECT 'CREATE DATABASE ${FLOWFORM_RESPONSE_DB}'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = '${FLOWFORM_RESPONSE_DB}'
)\gexec