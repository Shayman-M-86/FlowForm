#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

SECRET_FILE="${SECRET_FILE:-${PROJECT_ROOT}/infra/docker/secrets/DATABASE_RESPONSE_INIT_PASSWORD.dev.secret.txt}"
SQL_FILE="${1:-${SQL_FILE:-${PROJECT_ROOT}/infra/postgres/flowform_response_mock_data.sql}}"
CONTAINER_NAME="${CONTAINER_NAME:-flowform-postgres-response}"
DB_HOST="${DB_HOST:-localhost}"
DB_USER="${DB_USER:-flowform-admin}"
DB_NAME="${DB_NAME:-flowform_response}"
DB_SCHEMA="${DB_SCHEMA:-response_app, public}"

if [[ ! -f "${SECRET_FILE}" ]]; then
  echo "Secret file not found: ${SECRET_FILE}" >&2
  exit 1
fi

if [[ ! -f "${SQL_FILE}" ]]; then
  echo "SQL file not found: ${SQL_FILE}" >&2
  echo "Pass the response SQL file path as the first argument, or set SQL_FILE." >&2
  exit 1
fi

PASSWORD="$(<"${SECRET_FILE}")"
PASSWORD="${PASSWORD%$'\n'}"

(
  printf 'SET search_path TO %s;\n' "${DB_SCHEMA}"
  cat "${SQL_FILE}"
) | docker exec -e PGPASSWORD="${PASSWORD}" -i "${CONTAINER_NAME}" \
    psql -v ON_ERROR_STOP=1 -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}"
