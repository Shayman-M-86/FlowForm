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

# (b) the rehearsal proxy override mounts the BASE squid.conf (no fork).
grep -Fq '../services/squid/squid.conf:/etc/squid/squid.conf.template:ro' "${PROXY_OVERRIDE}" \
  || note "rehearsal proxy override no longer mounts the base squid.conf"
[[ -f "${SQUID_CONF}" ]] || note "base squid.conf missing at ${SQUID_CONF}"

# (c) the four backend secret _FILE env vars are identical in runtime and test.
secret_lines() {  # the four *_FILE=/run/secrets/... assignments, sorted
  grep -oE '(FLOWFORM_APP_SECRET_KEY|FLOWFORM_AUTH0_MGMT_SECRET|DATABASE_CORE_APP_PASSWORD|DATABASE_RESPONSE_APP_PASSWORD)_FILE: */run/secrets/[A-Z_]+' "$1" \
    | tr -d ' ' | sort -u
}
ref="$(secret_lines "${APP_COMPOSE}")"
[[ -n "${ref}" ]] || note "no secret _FILE env vars found in ${APP_COMPOSE##*/}"
for f in "${TEST_COMPOSE}"; do
  if [[ "$(secret_lines "$f")" != "${ref}" ]]; then
    note "secret _FILE env vars in ${f##*/} diverge from ${APP_COMPOSE##*/}"
  fi
done

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
