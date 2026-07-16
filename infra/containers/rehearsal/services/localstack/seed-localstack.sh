#!/usr/bin/env bash
set -Eeuo pipefail

# Seed the rehearsal LocalStack with the Secrets Manager secrets and SSM
# parameters the bootstrap scripts read. Run from the DEV BOX (it has plain `aws`
# → LocalStack via ~/.aws), or anywhere with AWS_ENDPOINT_URL pointed at LS.
#
# Populates EXACTLY the contract in infra/deployment/bootstrap/bootstrap-app.sh and
# bootstrap-proxy.sh:
#   Secrets Manager:
#     flowform/<scope>/app-secrets  {app_secret_key, auth0_mgmt_secret}
#     flowform/<scope>/db-secrets   {db_core_app_password, db_response_app_password}
#   SSM (String / SecureString) under:
#     /flowform/<scope>/backend/*   non-secret backend config
#     /flowform/<scope>/proxy/*     CADDY_IMAGE, API_DOMAIN
#
# Values are REHEARSAL THROWAWAYS — never real secrets. LocalStack has
# PERSISTENCE=0, so re-run this after every aws-fixtures-vm reboot.
#
# Idempotent: create-or-update for every secret/param.

: "${FLOWFORM_SCOPE:=nonprod}"
LS_ENDPOINT="${AWS_ENDPOINT_URL:-http://10.10.10.30:4566}"
REGION="${AWS_DEFAULT_REGION:-ap-southeast-2}"

# BACKEND_IMAGE / CADDY_IMAGE default to the fake-ECR registry on the
# aws-fixtures-vm (.30:5000) — the rehearsal delivers the backend image via that
# registry, not SSM. Overridable.
BACKEND_IMAGE="${BACKEND_IMAGE:-10.10.10.30:5000/flowform-backend:rehearsal}"
CADDY_IMAGE="${CADDY_IMAGE:-caddy:2-alpine}"
API_DOMAIN="${API_DOMAIN:-api.localstack.test}"

AWS=(aws --endpoint-url "${LS_ENDPOINT}" --region "${REGION}")
# Ensure creds exist even if ~/.aws isn't configured (e.g. run off the dev box).
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"

log() { printf '[seed-localstack] %s\n' "$*"; }
die() { printf '[seed-localstack] ERROR: %s\n' "$*" >&2; exit 1; }

# Preflight: LocalStack must be reachable and healthy.
curl -fsS --max-time 5 "${LS_ENDPOINT}/_localstack/health" >/dev/null 2>&1 \
  || die "LocalStack not reachable/healthy at ${LS_ENDPOINT} — start it on the ls-vm first"

# put_secret <name> <json-string> — create or update a Secrets Manager secret.
put_secret() {
  local name="$1" json="$2"
  if "${AWS[@]}" secretsmanager describe-secret --secret-id "${name}" >/dev/null 2>&1; then
    "${AWS[@]}" secretsmanager put-secret-value --secret-id "${name}" \
      --secret-string "${json}" --query 'VersionId' --output text >/dev/null
    log "updated secret ${name}"
  else
    "${AWS[@]}" secretsmanager create-secret --name "${name}" \
      --secret-string "${json}" --query 'ARN' --output text >/dev/null
    log "created secret ${name}"
  fi
}

# put_param <name> <value> <type> — create/overwrite an SSM parameter.
put_param() {
  local name="$1" value="$2" type="${3:-String}"
  "${AWS[@]}" ssm put-parameter --name "${name}" --value "${value}" \
    --type "${type}" --overwrite --query 'Version' --output text >/dev/null
  log "put param ${name} (${type})"
}

# rand <bytes> — a throwaway secret value (hex).
rand() { openssl rand -hex "${1:-32}"; }

log "scope=${FLOWFORM_SCOPE} endpoint=${LS_ENDPOINT}"

# --- Secrets Manager -------------------------------------------------------
# app-secrets: persistent/unregenerable values in the real system; throwaways here.
put_secret "flowform/${FLOWFORM_SCOPE}/app-secrets" \
  "$(printf '{"app_secret_key":"%s","auth0_mgmt_secret":"%s"}' "$(rand 32)" "$(rand 24)")"

# db-secrets: local Postgres app-user passwords (throwaways).
put_secret "flowform/${FLOWFORM_SCOPE}/db-secrets" \
  "$(printf '{"db_core_app_password":"%s","db_response_app_password":"%s"}' "$(rand 16)" "$(rand 16)")"

# --- SSM: backend/ (non-secret config the app renders into backend.env) ----
# This is the FULL config the backend needs to pass startup validation (env=prod).
# The backend's /health/ready only does a real `SELECT 1` on the two DBs; it does
# NOT call Auth0/KMS/SES at readiness. So Auth0/encryption/email values only need
# to be WELL-FORMED (validate as strings/ARNs), not functional — they're stubs /
# dev-tenant throwaways here. The DB parts, by contrast, ARE real (point at the
# app-box Postgres containers from docker-compose.app.rehearsal.yml).
BP="/flowform/${FLOWFORM_SCOPE}/backend"

# logging (all optional; set for parity with the real env). Note: the key is
# FLOWFORM_LOGGING_LEVEL, not _LOG_LEVEL.
put_param "${BP}/FLOWFORM_LOGGING_LOG_JSON" "true"
put_param "${BP}/FLOWFORM_LOGGING_LEVEL"    "INFO"

# FLOWFORM_ENV is the app's RUNTIME MODE (dev|test|prod) — a different axis from
# FLOWFORM_SCOPE (nonprod|prod, the secrets/param namespace). The rehearsal boots
# the prod runtime shape, so this is 'prod', NOT the scope. Overridable.
put_param "${BP}/FLOWFORM_ENV"    "${FLOWFORM_ENV:-prod}"
put_param "${BP}/BACKEND_IMAGE"   "${BACKEND_IMAGE}"

# Auth0 — dev-tenant throwaways (readiness doesn't call Auth0). MGMT secret comes
# from app-secrets (materialised to a tmpfs file), not here.
put_param "${BP}/FLOWFORM_AUTH0_DOMAIN"      "${FLOWFORM_AUTH0_DOMAIN:-dev-rehearsal.au.auth0.com}"
# Canonical tenant for the Management API (/api/v2 is not served on custom
# domains); mirrors the real backend config shape.
put_param "${BP}/FLOWFORM_AUTH0_MGMT_DOMAIN" "${FLOWFORM_AUTH0_MGMT_DOMAIN:-dev-rehearsal.au.auth0.com}"
put_param "${BP}/FLOWFORM_AUTH0_AUDIENCE"    "${FLOWFORM_AUTH0_AUDIENCE:-https://flowform.auth.api}"
put_param "${BP}/FLOWFORM_AUTH0_CLIENT_ID"   "${FLOWFORM_AUTH0_CLIENT_ID:-rehearsalClientId0000000000000000}"
put_param "${BP}/FLOWFORM_AUTH0_MGMT_ID"     "${FLOWFORM_AUTH0_MGMT_ID:-rehearsalMgmtId000000000000000000}"

# AWS + email (well-formed; not exercised at readiness).
put_param "${BP}/FLOWFORM_AWS_REGION"        "${REGION}"
put_param "${BP}/FLOWFORM_EMAIL_FROM_ADDRESS" "${FLOWFORM_EMAIL_FROM_ADDRESS:-no-reply@rehearsal.test}"

# Encryption — well-formed ARNs. These validate as strings at startup; readiness
# does not perform a KMS decrypt. Shaped like real ARNs so the config model accepts
# them. (A fuller rehearsal could create a real LocalStack KMS key + linkage secret
# and use those ARNs; not needed for a green /health/ready.)
put_param "${BP}/FLOWFORM_ENCRYPTION_KMS_KEY_ARN" \
  "${FLOWFORM_ENCRYPTION_KMS_KEY_ARN:-arn:aws:kms:${REGION}:000000000000:key/00000000-0000-0000-0000-000000000000}"
put_param "${BP}/FLOWFORM_ENCRYPTION_LINKAGE_SECRET_ARN" \
  "${FLOWFORM_ENCRYPTION_LINKAGE_SECRET_ARN:-arn:aws:secretsmanager:${REGION}:000000000000:secret:flowform/${FLOWFORM_SCOPE}/linkage-secret}"

# Database parts — REAL. Point at the app-box Postgres containers (service names
# core-db / response-db from docker-compose.app.rehearsal.yml). The app_user +
# db name must match what those containers are initialised with; the password is
# the same tmpfs secret both sides read.
put_param "${BP}/DATABASE_CORE_HOST"         "${DATABASE_CORE_HOST:-core-db}"
put_param "${BP}/DATABASE_CORE_NAME"         "flowform_core"
put_param "${BP}/DATABASE_CORE_APP_USER"     "flowform_core_app"
put_param "${BP}/DATABASE_RESPONSE_HOST"     "${DATABASE_RESPONSE_HOST:-response-db}"
put_param "${BP}/DATABASE_RESPONSE_NAME"     "flowform_response"
put_param "${BP}/DATABASE_RESPONSE_APP_USER" "flowform_response_app"

# --- SSM: proxy/ (CADDY_IMAGE + API_DOMAIN required by bootstrap-proxy) -----
PP="/flowform/${FLOWFORM_SCOPE}/proxy"
put_param "${PP}/CADDY_IMAGE" "${CADDY_IMAGE}"
put_param "${PP}/API_DOMAIN"  "${API_DOMAIN}"

log "done. Seeded secrets + params under flowform/${FLOWFORM_SCOPE}."
log "verify: aws --endpoint-url ${LS_ENDPOINT} ssm get-parameters-by-path --path ${BP}/ --recursive"
