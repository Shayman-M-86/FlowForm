#!/usr/bin/env bash
set -Eeuo pipefail

# Seed the rehearsal LocalStack with the Secrets Manager secrets and SSM
# parameters the bootstrap scripts read. Run from the DEV BOX (it has plain `aws`
# → LocalStack via ~/.aws), or anywhere with AWS_ENDPOINT_URL pointed at LS.
#
# Populates EXACTLY the contract in infra/scripts/bootstrap/bootstrap-app.sh and
# bootstrap-proxy.sh:
#   Secrets Manager:
#     flowform/<scope>/app-secrets  {app_secret_key, auth0_mgmt_secret}
#     flowform/<scope>/db-secrets   {db_core_app_password, db_response_app_password}
#   SSM (String / SecureString) under:
#     /flowform/<scope>/backend/*   non-secret backend config
#     /flowform/<scope>/proxy/*     CADDY_IMAGE, API_DOMAIN
#
# Values are REHEARSAL THROWAWAYS — never real secrets. LocalStack has
# PERSISTENCE=0, so re-run this after every ls-vm reboot.
#
# Idempotent: create-or-update for every secret/param.

: "${FLOWFORM_SCOPE:=nonprod}"
LS_ENDPOINT="${AWS_ENDPOINT_URL:-http://10.10.10.30:4566}"
REGION="${AWS_DEFAULT_REGION:-ap-southeast-2}"

# BACKEND_IMAGE / CADDY_IMAGE default to the private registry on the proxy — the
# rehearsal delivers the backend image via registry, not SSM. Overridable.
BACKEND_IMAGE="${BACKEND_IMAGE:-10.10.10.10:5000/flowform-backend:rehearsal}"
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
BP="/flowform/${FLOWFORM_SCOPE}/backend"
put_param "${BP}/FLOWFORM_LOGGING_LOG_JSON"  "true"
put_param "${BP}/FLOWFORM_LOGGING_LOG_LEVEL" "INFO"
put_param "${BP}/FLOWFORM_ENV"               "${FLOWFORM_SCOPE}"
put_param "${BP}/BACKEND_IMAGE"              "${BACKEND_IMAGE}"

# --- SSM: proxy/ (CADDY_IMAGE + API_DOMAIN required by bootstrap-proxy) -----
PP="/flowform/${FLOWFORM_SCOPE}/proxy"
put_param "${PP}/CADDY_IMAGE" "${CADDY_IMAGE}"
put_param "${PP}/API_DOMAIN"  "${API_DOMAIN}"

log "done. Seeded secrets + params under flowform/${FLOWFORM_SCOPE}."
log "verify: aws --endpoint-url ${LS_ENDPOINT} ssm get-parameters-by-path --path ${BP}/ --recursive"
