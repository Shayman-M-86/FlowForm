#!/usr/bin/env bash
set -Eeuo pipefail

# Guard the container-unification invariants: the artifacts that are shared
# BY CONSTRUCTION across dev / rehearsal / live must not silently fork. Each
# check fails loudly the moment "unified" stops being true, so a future edit
# cannot quietly reintroduce the drift this reunification removed.
#
# What is DELIBERATELY separate (NOT asserted here, by design):
#   - the two compose bases: dev (bind-mount/debug) vs deployment (hardened).
#   - rehearsal postgres: a dedicated RDS stand-in using the maintained init
#     tree and a Packer-preloaded image on isolated VM 240.
#   - backend.test.Dockerfile: test extras (--extra test) + bash CMD.
#   - dev's whole-dir secret bind (documented Docker-Desktop/WSL bind bug).
#   - the Caddyfile issuer line + squid allow-list CONTENTS (env-specific).
#   - rehearsal fixtures (localstack / registry / tls-shim / schema-init).

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
FAIL=0
note() { printf 'FAIL: %s\n' "$*" >&2; FAIL=1; }

CADDY_PROD="${REPO_ROOT}/infra/containers/strategies/aws/services/caddy/Caddyfile.proxy"
CADDY_REH="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/caddy/Caddyfile.proxy"
SQUID_CONF="${REPO_ROOT}/infra/containers/runtime/services/squid/squid.conf"
PROXY_COMPOSE="${REPO_ROOT}/infra/containers/runtime/compose/proxy.yml"
PROXY_OVERRIDE="${REPO_ROOT}/infra/containers/strategies/rehearsal/compose/proxy.override.yml"
PUSH_SCRIPT="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/registry/build-and-push-backend.sh"
BACKEND_DOCKERFILE="infra/containers/images/backend/backend.Dockerfile"
APP_COMPOSE="${REPO_ROOT}/infra/containers/runtime/compose/app.yml"
TEST_COMPOSE="${REPO_ROOT}/infra/containers/strategies/dev/compose/compose.test.yml"
DB_COMPOSE="${REPO_ROOT}/infra/containers/strategies/rehearsal/compose/db.yml"
DEV_COMPOSE="${REPO_ROOT}/infra/containers/strategies/dev/compose/compose.yml"

# (a) prod and rehearsal proxy Caddyfiles differ ONLY in the tls issuer.
# Compare with comment + blank lines and the tls block stripped; the remainder
# (headers, reverse_proxy, health checks) must be byte-identical.
strip_caddy() {  # drop comments/blanks and the tls directive (line or block)
  awk '
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*$/ { next }
    /^[[:space:]]*tls[[:space:]]/ { if ($0 ~ /\{[[:space:]]*$/) intls=1; next }
    intls && /^[[:space:]]*\}/ { intls=0; next }
    intls { next }
    { print }
  ' "$1"
}
if ! diff <(strip_caddy "${CADDY_PROD}") <(strip_caddy "${CADDY_REH}") >/dev/null; then
  note "prod and rehearsal Caddyfile.proxy differ beyond the tls issuer line"
  diff <(strip_caddy "${CADDY_PROD}") <(strip_caddy "${CADDY_REH}") | sed 's/^/    /' >&2
fi
for caddy_file in "${CADDY_PROD}" "${CADDY_REH}"; do
  grep -Fq 'request>uri regexp "^(/api/v1/account/invitations/resolve/)[^/?]+" "${1}[REDACTED]"' "${caddy_file}" \
    || note "${caddy_file##*/} no longer redacts invitation tokens from Caddy error URIs"
  grep -Fq 'request>headers>Referer replace REDACTED' "${caddy_file}" \
    || note "${caddy_file##*/} no longer removes Referer values from Caddy error logs"
done

# (b) the rehearsal proxy override mounts the BASE squid.conf (no fork).
grep -Fq '../services/squid/squid.conf:/etc/squid/squid.conf.template:ro' "${PROXY_OVERRIDE}" \
  || note "rehearsal proxy override no longer mounts the base squid.conf"
[[ -f "${SQUID_CONF}" ]] || note "base squid.conf missing at ${SQUID_CONF}"
grep -Fq 'access_log stdio:/var/log/squid/access.log flowform_access' "${SQUID_CONF}" \
  || note "squid file access log required by rehearsal verify is missing"
grep -Fq 'logformat flowform_access level=info' "${SQUID_CONF}" \
  || note "squid access log no longer carries a Grafana severity"
grep -Fq "su -s /bin/sh -c 'exec tail -n 0 -F /var/log/squid/access.log' proxy &" "${PROXY_COMPOSE}" \
  || note "squid access logs are no longer exposed to Docker/Alloy"

# (c) runtime keeps its four file-backed secrets; tests share only the DB/app
# files and use a direct, throwaway Auth0 value with live validation disabled.
shared_secret_lines() {  # the three shared *_FILE assignments, sorted
  grep -oE '(FLOWFORM_APP_SECRET_KEY|DATABASE_CORE_APP_PASSWORD|DATABASE_RESPONSE_APP_PASSWORD)_FILE: */run/secrets/[A-Z_]+' "$1" \
    | tr -d ' ' | sort -u
}
ref="$(shared_secret_lines "${APP_COMPOSE}")"
[[ "$(printf '%s\n' "${ref}" | sed '/^$/d' | wc -l)" -eq 3 ]] \
  || note "runtime compose no longer has the three shared DB/app secret files"
[[ "$(shared_secret_lines "${TEST_COMPOSE}")" == "${ref}" ]] \
  || note "shared DB/app secret _FILE env vars in test compose diverge from runtime"

grep -Fq 'FLOWFORM_AUTH0_MGMT_SECRET_FILE: /run/secrets/FLOWFORM_AUTH0_MGMT_SECRET' "${APP_COMPOSE}" \
  || note "runtime compose no longer requires its file-backed Auth0 management secret"
grep -Fq 'FLOWFORM_AUTH0_MGMT_SECRET: ${FLOWFORM_TEST_AUTH0_MGMT_SECRET:-flowform-local-test-auth0-secret}' "${TEST_COMPOSE}" \
  || note "test compose no longer uses the direct throwaway Auth0 management secret"
grep -Fq 'FLOWFORM_AUTH0_MGMT_SECRET_FILE: ""' "${TEST_COMPOSE}" \
  || note "test compose no longer clears the inherited Auth0 secret-file setting"
grep -Fq 'FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP: "false"' "${TEST_COMPOSE}" \
  || note "test compose no longer disables live Auth0 management validation"
if grep -Eq '^[[:space:]]+- FLOWFORM_AUTH0_MGMT_SECRET$' "${TEST_COMPOSE}"; then
  note "test compose still mounts an Auth0 management secret file"
fi

# (d) rehearsal DB is an offline, single-cluster fixture using the real init tree.
grep -Fq 'image: postgres:17' "${DB_COMPOSE}" || note "rehearsal DB image is not postgres:17"
grep -Fq 'pull_policy: never' "${DB_COMPOSE}" || note "rehearsal DB can pull at runtime"
grep -Fq 'DATABASE_INIT_TARGET: all' "${DB_COMPOSE}" || note "rehearsal DB does not initialise both databases"
grep -Fq 'ipv4_address: 172.60.0.2' "${DB_COMPOSE}" || note "rehearsal DB lost its enforced container address"

# (e) the push script builds the single backend Dockerfile (one backend image def).
grep -Fq "${BACKEND_DOCKERFILE}" "${PUSH_SCRIPT}" \
  || note "build-and-push-backend.sh no longer builds ${BACKEND_DOCKERFILE}"
[[ -f "${REPO_ROOT}/${BACKEND_DOCKERFILE}" ]] \
  || note "single backend Dockerfile missing at ${BACKEND_DOCKERFILE}"

# (f) dev and runtime compose reference the SAME healthcheck script.
grep -Fq '/app/scripts/healthcheck.py' "${DEV_COMPOSE}" \
  || note "dev compose no longer uses /app/scripts/healthcheck.py"
grep -Fq '/app/scripts/healthcheck.py' "${APP_COMPOSE}" \
  || note "runtime compose no longer uses /app/scripts/healthcheck.py"

if (( FAIL == 0 )); then
  printf '[test-container-invariants] PASS\n'
else
  printf '[test-container-invariants] FAIL\n' >&2
  exit 1
fi
