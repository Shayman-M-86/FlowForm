#!/usr/bin/env bash
set -Eeuo pipefail

# Guard the container-unification invariants: the artifacts that are shared
# BY CONSTRUCTION across dev / rehearsal / live must not silently fork. Each
# check fails loudly the moment "unified" stops being true, so a future edit
# cannot quietly reintroduce the drift this reunification removed.
#
# What is DELIBERATELY separate (NOT asserted here, by design):
#   - the two compose bases: dev (bind-mount/debug) vs deployment (hardened).
#   - rehearsal postgres (core-db/response-db): an RDS stand-in — app-user-only,
#     tmpfs, schema via SQLAlchemy create_all. Unifying it with dev/test
#     postgres would destroy the fidelity boundary.
#   - backend.test.Dockerfile: test extras (--extra test) + bash CMD.
#   - dev's whole-dir secret bind (documented Docker-Desktop/WSL bind bug).
#   - the Caddyfile issuer line + squid allow-list CONTENTS (env-specific).
#   - rehearsal fixtures (localstack / registry / tls-shim / schema-init).

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
FAIL=0
note() { printf 'FAIL: %s\n' "$*" >&2; FAIL=1; }

CADDY_PROD="${REPO_ROOT}/infra/containers/deployment/services/caddy/Caddyfile.proxy"
CADDY_REH="${REPO_ROOT}/infra/containers/rehearsal/services/caddy/Caddyfile.proxy"
SQUID_CONF="${REPO_ROOT}/infra/containers/deployment/services/squid/squid.conf"
PROXY_OVERRIDE="${REPO_ROOT}/infra/containers/rehearsal/compose/compose.proxy.rehearsal.yml"
PUSH_SCRIPT="${REPO_ROOT}/infra/containers/rehearsal/services/registry/build-and-push-backend.sh"
BACKEND_DOCKERFILE="infra/containers/dev/services/backend/backend.Dockerfile"
APP_COMPOSE="${REPO_ROOT}/infra/containers/deployment/compose/compose.app.yml"
TEST_COMPOSE="${REPO_ROOT}/infra/containers/dev/compose/compose.test.yml"
APP_REHEARSAL="${REPO_ROOT}/infra/containers/rehearsal/compose/compose.app.rehearsal.yml"
DEV_COMPOSE="${REPO_ROOT}/infra/containers/dev/compose/compose.yml"

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

# (b) the rehearsal proxy override mounts the BASE squid.conf (no fork).
grep -Fq '../services/squid/squid.conf:/etc/squid/squid.conf.template:ro' "${PROXY_OVERRIDE}" \
  || note "rehearsal proxy override no longer mounts the base squid.conf"
[[ -f "${SQUID_CONF}" ]] || note "base squid.conf missing at ${SQUID_CONF}"

# (c) the four secret _FILE env vars are identical across every backend/schema-init
#     definition (byte-identical /run/secrets paths).
secret_lines() {  # the four *_FILE=/run/secrets/... assignments, sorted
  grep -oE '(FLOWFORM_APP_SECRET_KEY|FLOWFORM_AUTH0_MGMT_SECRET|DATABASE_CORE_APP_PASSWORD|DATABASE_RESPONSE_APP_PASSWORD)_FILE: */run/secrets/[A-Z_]+' "$1" \
    | tr -d ' ' | sort -u
}
ref="$(secret_lines "${APP_COMPOSE}")"
[[ -n "${ref}" ]] || note "no secret _FILE env vars found in ${APP_COMPOSE##*/}"
for f in "${TEST_COMPOSE}" "${APP_REHEARSAL}"; do
  if [[ "$(secret_lines "$f")" != "${ref}" ]]; then
    note "secret _FILE env vars in ${f##*/} diverge from ${APP_COMPOSE##*/}"
  fi
done

# (d) the push script builds the single backend Dockerfile (one backend image def).
grep -Fq "${BACKEND_DOCKERFILE}" "${PUSH_SCRIPT}" \
  || note "build-and-push-backend.sh no longer builds ${BACKEND_DOCKERFILE}"
[[ -f "${REPO_ROOT}/${BACKEND_DOCKERFILE}" ]] \
  || note "single backend Dockerfile missing at ${BACKEND_DOCKERFILE}"

# (e) dev and runtime compose reference the SAME healthcheck script.
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
