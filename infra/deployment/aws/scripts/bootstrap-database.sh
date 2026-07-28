#!/usr/bin/env bash
set -Eeuo pipefail

# FlowForm RDS database bootstrap.
#
# Creates the logical databases, roles, schemas, grants, and IAM authentication
# for a deployed RDS instance. This is a REMOTE operator/release operation: it
# runs from a workstation or a release job that can reach the RDS endpoint, not
# on a database host. RDS provides no host to run anything on, which is why this
# lives under the AWS deployment scripts rather than beside the rehearsal
# bootstrap.
#
# Boundary:
#   - the SQL it executes lives in infra/database/init/aws/ (database logic)
#   - this script owns endpoint discovery, credentials, ordering, and checks
#     (deployment logic)
#
# CDK provisions the RDS service and the admin credential; this script owns the
# database contents. Keeping them separate is deliberate: CloudFormation must
# not mutate application schemas.
#
# Idempotent: safe to re-run against an already-bootstrapped instance.
#
# Usage:
#   infra/deployment/aws/scripts/bootstrap-database.sh [--env staging] [--apply]
#
# Dry run by default: resolves inputs and prints the steps without connecting.

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." >/dev/null 2>&1 && pwd)"
SQL_DIR="${REPO_ROOT}/infra/database/init/aws"
SCHEMA_DIR="${REPO_ROOT}/infra/database/init/schema"

ENV_NAME="staging"
APPLY=false

CORE_DB="flowform_core"
RESPONSE_DB="flowform_response"
CORE_SCHEMA="core_app"
RESPONSE_SCHEMA="response_app"
CORE_APP_USER="flowform_core_app"
RESPONSE_APP_USER="flowform_response_app"
CORE_SCHEMA_FILE="${SCHEMA_DIR}/flowform_core_db_schema_v4.sql"
RESPONSE_SCHEMA_FILE="${SCHEMA_DIR}/flowform_response_db_schema_v4.sql"

log()  { printf '[bootstrap-database] %s\n' "$*"; }
die()  { printf '[bootstrap-database] ERROR: %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)   ENV_NAME="${2:?--env needs a value}"; shift 2 ;;
    --apply) APPLY=true; shift ;;
    -h|--help)
      sed -n '4,28p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *) die "unknown argument: $1" ;;
  esac
done

command -v aws  >/dev/null || die "aws CLI is required"
command -v jq   >/dev/null || die "jq is required"
command -v psql >/dev/null || die "psql is required (postgresql client)"

for sql in 01-bootstrap-roles 02-create-databases 03-load-schema 04-grant-permissions 05-verify; do
  [[ -f "${SQL_DIR}/${sql}.sql" ]] || die "missing SQL step: ${SQL_DIR}/${sql}.sql"
done
[[ -f "${CORE_SCHEMA_FILE}" ]]     || die "missing core schema: ${CORE_SCHEMA_FILE}"
[[ -f "${RESPONSE_SCHEMA_FILE}" ]] || die "missing response schema: ${RESPONSE_SCHEMA_FILE}"

# ---------------------------------------------------------------------------
# Resolve the instance and its RDS-managed admin credential.
# ---------------------------------------------------------------------------

DB_IDENTIFIER="flowform-${ENV_NAME}-postgres"

log "resolving RDS instance ${DB_IDENTIFIER}"
instance_json="$(
  aws rds describe-db-instances \
    --db-instance-identifier "${DB_IDENTIFIER}" \
    --query 'DBInstances[0].{addr:Endpoint.Address,port:Endpoint.Port,secret:MasterUserSecret.SecretArn,iam:IAMDatabaseAuthenticationEnabled}' \
    --output json
)" || die "could not describe ${DB_IDENTIFIER}; is it deployed?"

DB_HOST="$(jq -r '.addr'   <<<"${instance_json}")"
DB_PORT="$(jq -r '.port'   <<<"${instance_json}")"
SECRET_ARN="$(jq -r '.secret' <<<"${instance_json}")"
IAM_ENABLED="$(jq -r '.iam'  <<<"${instance_json}")"

[[ "${DB_HOST}" != "null" ]]    || die "instance has no endpoint yet"
[[ "${SECRET_ARN}" != "null" ]] || die "instance has no RDS-managed master secret"

# The runtime roles authenticate only with IAM tokens. Bootstrapping them
# against an instance without IAM auth would produce roles nothing can log in
# as, so stop before making that state.
[[ "${IAM_ENABLED}" == "true" ]] \
  || die "IAM database authentication is not enabled on ${DB_IDENTIFIER}; deploy the DatabaseStack change first"

log "endpoint      ${DB_HOST}:${DB_PORT}"
log "admin secret  ${SECRET_ARN}"

if [[ "${APPLY}" != true ]]; then
  log ""
  log "DRY RUN — would run, as flowform_admin over TLS:"
  log "  1. ${SQL_DIR}/01-bootstrap-roles.sql      (owner, runtime roles, rds_iam)"
  log "  2. ${SQL_DIR}/02-create-databases.sql     (databases, REVOKE PUBLIC CONNECT)"
  log "  3. ${SQL_DIR}/03-load-schema.sql          (per database, objects under SET ROLE)"
  log "  4. ${SQL_DIR}/04-grant-permissions.sql    (per database, runtime grants)"
  log "  5. ${SQL_DIR}/05-verify.sql               (role and isolation invariants)"
  log "  6. live connection checks for both runtime identities"
  log ""
  log "re-run with --apply to execute"
  exit 0
fi

# ---------------------------------------------------------------------------
# Execute.
# ---------------------------------------------------------------------------

# The admin password is held in an exported variable and passed to psql through
# PGPASSWORD so it never appears in argv or the process table. It is unset as
# soon as the SQL steps finish.
PGPASSWORD="$(
  aws secretsmanager get-secret-value \
    --secret-id "${SECRET_ARN}" \
    --query SecretString --output text | jq -r '.password'
)" || die "could not read the RDS-managed admin secret"
export PGPASSWORD
trap 'unset PGPASSWORD' EXIT

ADMIN_USER="flowform_admin"
# verify-full requires the RDS CA bundle; sslrootcert is left to the caller's
# environment (PGSSLROOTCERT) so this script does not bake in a CA path.
PSQL_BASE=(psql --host "${DB_HOST}" --port "${DB_PORT}" --username "${ADMIN_USER}"
           --set ON_ERROR_STOP=1 --no-password --quiet
           --set sslmode="${PGSSLMODE:-verify-full}")

run_sql() { # $1 database  $2 sql file  [extra --set args...]
  local database="$1" sql_file="$2"; shift 2
  "${PSQL_BASE[@]}" --dbname "${database}" "$@" --file "${sql_file}"
}

log "step 1/6: roles and IAM authentication"
run_sql postgres "${SQL_DIR}/01-bootstrap-roles.sql"

log "step 2/6: databases and connection isolation"
run_sql postgres "${SQL_DIR}/02-create-databases.sql"

log "step 3/6: schema load"
run_sql "${CORE_DB}" "${SQL_DIR}/03-load-schema.sql" \
  --set app_schema="${CORE_SCHEMA}" --set schema_file="${CORE_SCHEMA_FILE}"
run_sql "${RESPONSE_DB}" "${SQL_DIR}/03-load-schema.sql" \
  --set app_schema="${RESPONSE_SCHEMA}" --set schema_file="${RESPONSE_SCHEMA_FILE}"

log "step 4/6: runtime grants"
run_sql "${CORE_DB}" "${SQL_DIR}/04-grant-permissions.sql" \
  --set app_schema="${CORE_SCHEMA}" --set app_user="${CORE_APP_USER}"
run_sql "${RESPONSE_DB}" "${SQL_DIR}/04-grant-permissions.sql" \
  --set app_schema="${RESPONSE_SCHEMA}" --set app_user="${RESPONSE_APP_USER}"

log "step 5/6: catalogue verification"
run_sql postgres "${SQL_DIR}/05-verify.sql"

unset PGPASSWORD
trap - EXIT

# ---------------------------------------------------------------------------
# Live connection checks.
#
# The catalogue verification proves the grants are recorded; only a real
# connection proves a runtime identity can authenticate with an IAM token and
# that it cannot reach the other database.
# ---------------------------------------------------------------------------

check_iam_login() { # $1 db  $2 user  $3 expect: allow|deny
  local database="$1" user="$2" expect="$3" token rc=0
  token="$(aws rds generate-db-auth-token \
    --hostname "${DB_HOST}" --port "${DB_PORT}" --username "${user}")" \
    || die "could not generate an IAM token for ${user}"

  PGPASSWORD="${token}" psql \
    --host "${DB_HOST}" --port "${DB_PORT}" --username "${user}" \
    --dbname "${database}" --no-password --quiet \
    --set sslmode="${PGSSLMODE:-verify-full}" \
    --command 'SELECT 1;' >/dev/null 2>&1 || rc=$?

  if [[ "${expect}" == "allow" ]]; then
    ((rc == 0)) || die "${user} could not authenticate to ${database} with an IAM token"
    log "  ${user} -> ${database}: connected"
  else
    ((rc != 0)) || die "${user} reached ${database}; database isolation is broken"
    log "  ${user} -> ${database}: correctly refused"
  fi
}

log "step 6/6: live IAM connection checks"
check_iam_login "${CORE_DB}"     "${CORE_APP_USER}"     allow
check_iam_login "${RESPONSE_DB}" "${RESPONSE_APP_USER}" allow
check_iam_login "${RESPONSE_DB}" "${CORE_APP_USER}"     deny
check_iam_login "${CORE_DB}"     "${RESPONSE_APP_USER}" deny

log "database bootstrap complete for ${ENV_NAME}"
