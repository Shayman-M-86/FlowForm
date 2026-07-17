#!/usr/bin/env bash
set -Eeuo pipefail

# Run terraform with the Auth0 values from the dev backend env exported as
# TF_VAR_* — so the rehearsal validates tokens against the same tenant your dev
# stack does, without those values being committed.
#
# Why sourced rather than defaulted in variables.tf: the rehearsal is only
# useful if it accepts the tokens your Studio front end already issues, which
# means issuer + audience + client id must match dev exactly. Duplicating them
# into a committed default guarantees they drift the first time either side
# changes tenant; reading the one file dev already reads means they cannot.
#
# infra/env/dev/.backend.env is gitignored (.gitignore: env/), so nothing here
# lands in git. These are non-secret identifiers — domains, audience, client id.
# The Auth0 mgmt CLIENT SECRET is deliberately NOT handled here: it lives in
# AWS Secrets Manager and is fetched by scripts/secrets/fetch-dev-secrets.sh
# into a tmpfs. The rehearsal seeds its own random mgmt secret, so Management
# API calls do not work there — see FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP in
# variables.tf.
#
# Usage:
#   with-dev-auth0-env.sh plan
#   with-dev-auth0-env.sh apply -auto-approve
#
# Override the source file with DEV_BACKEND_ENV=/path/to/.backend.env.

log() { printf '[with-dev-auth0-env] %s\n' "$*" >&2; }
die() { printf '[with-dev-auth0-env] ERROR: %s\n' "$*" >&2; exit 1; }

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${HERE}/../../../.." && pwd)"
DEV_BACKEND_ENV="${DEV_BACKEND_ENV:-${REPO_ROOT}/infra/env/dev/.backend.env}"

[[ -f "${DEV_BACKEND_ENV}" ]] || die "dev backend env not found: ${DEV_BACKEND_ENV}
  This file is gitignored and machine-local. Create it as you would for the dev
  stack, or point at another with DEV_BACKEND_ENV=."

# dev env var  ->  terraform variable
declare -A WANTED=(
  [FLOWFORM_AUTH0_DOMAIN]=auth0_domain
  [FLOWFORM_AUTH0_AUDIENCE]=auth0_audience
  [FLOWFORM_AUTH0_CLIENT_ID]=auth0_client_id
  [FLOWFORM_AUTH0_MGMT_DOMAIN]=auth0_mgmt_domain
  [FLOWFORM_AUTH0_MGMT_ID]=auth0_mgmt_id
)

# Read only the keys we want rather than sourcing the file: it is a compose
# env_file, not a shell script — unquoted values with spaces or a stray `$`
# would execute or mangle under `source`.
for key in "${!WANTED[@]}"; do
  line="$(grep -E "^${key}=" "${DEV_BACKEND_ENV}" | tail -n1 || true)"
  [[ -n "${line}" ]] || die "${key} not set in ${DEV_BACKEND_ENV}"

  value="${line#*=}"
  value="${value%$'\r'}"                 # tolerate CRLF
  value="${value#[\"\']}"; value="${value%[\"\']}"  # strip matching quotes

  [[ -n "${value}" ]] || die "${key} is empty in ${DEV_BACKEND_ENV}"

  export "TF_VAR_${WANTED[$key]}=${value}"
done

log "Auth0 vars sourced from ${DEV_BACKEND_ENV#"${REPO_ROOT}/"}"
log "issuer: ${TF_VAR_auth0_domain} | mgmt: ${TF_VAR_auth0_mgmt_domain}"

exec terraform -chdir="${HERE}" "$@"
