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

CADDY_AWS="${REPO_ROOT}/infra/containers/strategies/aws/services/caddy/Caddyfile.proxy"
CADDY_REH="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/caddy/Caddyfile.proxy"
SQUID_CONF="${REPO_ROOT}/infra/containers/runtime/services/squid/squid.conf"
PROXY_COMPOSE="${REPO_ROOT}/infra/containers/runtime/compose/proxy.yml"
AWS_PROXY_OVERRIDE="${REPO_ROOT}/infra/containers/strategies/aws/compose/proxy.override.yml"
PROXY_OVERRIDE="${REPO_ROOT}/infra/containers/strategies/rehearsal/compose/proxy.override.yml"
BOOTSTRAP_PROXY="${REPO_ROOT}/infra/deployment/bootstrap/bootstrap-proxy.sh"
PUSH_SCRIPT="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/registry/build-and-push-backend.sh"
BACKEND_DOCKERFILE="infra/containers/images/backend/backend.Dockerfile"
CADDY_DOCKERFILE="${REPO_ROOT}/infra/containers/strategies/aws/services/caddy/caddy.Dockerfile"
AWS_IMAGE_MANIFEST="${REPO_ROOT}/infra/containers/strategies/aws/image-sources.json"
AWS_IMAGE_PUBLISHER="${REPO_ROOT}/infra/deployment/aws/scripts/publish-staging-images.sh"
APP_COMPOSE="${REPO_ROOT}/infra/containers/runtime/compose/app.yml"
TEST_COMPOSE="${REPO_ROOT}/infra/containers/strategies/dev/compose/compose.test.yml"
DB_COMPOSE="${REPO_ROOT}/infra/containers/strategies/rehearsal/compose/db.yml"
DEV_COMPOSE="${REPO_ROOT}/infra/containers/strategies/dev/compose/compose.yml"

# (a) AWS and rehearsal proxy Caddyfiles differ ONLY in the TLS mechanism.
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
if ! diff <(strip_caddy "${CADDY_AWS}") <(strip_caddy "${CADDY_REH}") >/dev/null; then
  note "AWS and rehearsal Caddyfile.proxy differ beyond the TLS mechanism"
  diff <(strip_caddy "${CADDY_AWS}") <(strip_caddy "${CADDY_REH}") | sed 's/^/    /' >&2
fi
grep -Fq $'\t\tdns route53' "${CADDY_AWS}" \
  || note "AWS Caddyfile no longer uses the Route 53 DNS provider"
grep -Fq $'\ttls /etc/caddy/certs/api.crt /etc/caddy/certs/api.key' "${CADDY_REH}" \
  || note "rehearsal Caddyfile no longer uses the committed certificate paths"
for caddy_file in "${CADDY_AWS}" "${CADDY_REH}"; do
  grep -Fq 'request>uri regexp "^(/api/v1/account/invitations/resolve/)[^/?]+" "${1}[REDACTED]"' "${caddy_file}" \
    || note "${caddy_file##*/} no longer redacts invitation tokens from Caddy error URIs"
  grep -Fq 'request>headers>Referer replace REDACTED' "${caddy_file}" \
    || note "${caddy_file##*/} no longer removes Referer values from Caddy error logs"
done

# (b) the shared proxy base remains strategy-neutral; AWS and rehearsal each
# select exactly their own Caddyfile and Squid destination allow-list.
[[ -f "${AWS_PROXY_OVERRIDE}" ]] || note "AWS proxy override is missing"
if grep -Eq '\.\./\.\./strategies/(aws|rehearsal)/services/' "${PROXY_COMPOSE}"; then
  note "shared proxy compose directly references a deployment strategy"
fi
grep -Fq '../services/squid/squid.conf:/etc/squid/squid.conf.template:ro' "${PROXY_COMPOSE}" \
  || note "shared proxy compose no longer mounts the shared squid.conf"
grep -Fq '../../strategies/aws/services/caddy/Caddyfile.proxy:/etc/caddy/Caddyfile:ro' "${AWS_PROXY_OVERRIDE}" \
  || note "AWS proxy override no longer selects the AWS Caddyfile"
grep -Fq '../../strategies/aws/services/squid/allowed-domains.txt:/etc/squid/allowed-domains.txt:ro' "${AWS_PROXY_OVERRIDE}" \
  || note "AWS proxy override no longer selects the AWS Squid allow-list"
grep -Fq '../../strategies/rehearsal/services/caddy/Caddyfile.proxy:/etc/caddy/Caddyfile:ro' "${PROXY_OVERRIDE}" \
  || note "rehearsal proxy override no longer selects the rehearsal Caddyfile"
grep -Fq '../../strategies/rehearsal/services/squid/allowed-domains.txt:/etc/squid/allowed-domains.txt:ro' "${PROXY_OVERRIDE}" \
  || note "rehearsal proxy override no longer selects the rehearsal Squid allow-list"
grep -Fq 'infra/containers/strategies/aws/compose/proxy.override.yml}' "${BOOTSTRAP_PROXY}" \
  || note "proxy bootstrap no longer defaults to the AWS strategy override"
[[ -f "${SQUID_CONF}" ]] || note "base squid.conf missing at ${SQUID_CONF}"
grep -Fq 'access_log stdio:/var/log/squid/access.log flowform_access' "${SQUID_CONF}" \
  || note "squid file access log required by rehearsal verify is missing"
if grep -Eq '^logformat flowform_access .*level=' "${SQUID_CONF}"; then
  note "squid access log again embeds a duplicate severity field"
fi
grep -Fq 'selector = "{service_name=\"squid\"}"' "${REPO_ROOT}/infra/containers/runtime/services/alloy/config.alloy" \
  || note "proxy Alloy no longer selects every Squid stream for severity tagging"
grep -Fq 'level = "info",' "${REPO_ROOT}/infra/containers/runtime/services/alloy/config.alloy" \
  || note "proxy Alloy no longer applies the static Squid severity"
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

# (f) AWS Caddy is reproducible and contains the Route 53 DNS provider required
# by the AWS Caddyfile. Rehearsal intentionally remains stock Caddy
# because it replaces DNS-01 with its committed test certificate.
[[ -f "${CADDY_DOCKERFILE}" ]] || note "AWS Caddy Dockerfile missing at ${CADDY_DOCKERFILE}"
grep -Eq '^FROM caddy:2\.11\.4-builder-alpine@sha256:[0-9a-f]{64} AS builder$' "${CADDY_DOCKERFILE}" \
  || note "AWS Caddy builder base is not pinned to the approved version and digest"
grep -Eq '^FROM caddy:2\.11\.4-alpine@sha256:[0-9a-f]{64}$' "${CADDY_DOCKERFILE}" \
  || note "AWS Caddy runtime base is not pinned to the approved version and digest"
grep -Fq 'xcaddy build v2.11.4' "${CADDY_DOCKERFILE}" \
  || note "AWS Caddy core version is not pinned"
grep -Fq -- '--with github.com/caddy-dns/route53@v1.6.2' "${CADDY_DOCKERFILE}" \
  || note "AWS Caddy Route 53 module version is not pinned"
grep -Fq "caddy list-modules | grep -Fxq 'dns.providers.route53'" "${CADDY_DOCKERFILE}" \
  || note "AWS Caddy build does not verify the Route 53 module"
if grep -Eq '(^|[[:space:]:@])latest([[:space:]@]|$)' "${CADDY_DOCKERFILE}"; then
  note "AWS Caddy Dockerfile contains a floating latest reference"
fi

# (g) every AWS runtime image has one checked-in immutable linux/amd64 source
# declaration, and deployed Compose refuses to start without image selection.
[[ -f "${AWS_IMAGE_MANIFEST}" ]] || note "AWS image source manifest is missing"
[[ -x "${AWS_IMAGE_PUBLISHER}" ]] || note "AWS image publisher is missing or not executable"
jq -e '
  .schema_version == 1
  and .platform.buildx == "linux/amd64"
  and (.images | keys == ["alloy", "backend", "caddy", "squid"])
  and ([
    .images.backend.sources[],
    .images.caddy.sources[],
    .images.squid.source,
    .images.alloy.source
  ] | all(
    (.reference | contains(":latest") | not)
    and (.index_digest | test("^sha256:[0-9a-f]{64}$"))
    and (.platform_digest | test("^sha256:[0-9a-f]{64}$"))
  ))
' "${AWS_IMAGE_MANIFEST}" >/dev/null \
  || note "AWS image source manifest is incomplete, floating, or not linux/amd64"
grep -Eq '^FROM python:3\.14\.6-slim-trixie@sha256:[0-9a-f]{64}$' "${REPO_ROOT}/${BACKEND_DOCKERFILE}" \
  || note "Backend Python base is not pinned to the approved version and digest"
grep -Eq '^COPY --from=ghcr\.io/astral-sh/uv:0\.11\.31@sha256:[0-9a-f]{64} ' "${REPO_ROOT}/${BACKEND_DOCKERFILE}" \
  || note "Backend uv source is not pinned to the approved version and digest"
grep -Fq 'image: ${BACKEND_IMAGE:?set BACKEND_IMAGE to the backend ECR ref}' "${APP_COMPOSE}" \
  || note "app Compose no longer requires explicit Backend image selection"
grep -Fq 'image: ${ALLOY_IMAGE:?set ALLOY_IMAGE}' "${APP_COMPOSE}" \
  || note "app Compose no longer requires explicit Alloy image selection"
grep -Fq 'image: ${CADDY_IMAGE:?set CADDY_IMAGE}' "${PROXY_COMPOSE}" \
  || note "proxy Compose no longer requires explicit Caddy image selection"
grep -Fq 'image: ${SQUID_IMAGE:?set SQUID_IMAGE}' "${PROXY_COMPOSE}" \
  || note "proxy Compose no longer requires explicit Squid image selection"
grep -Fq 'image: ${ALLOY_IMAGE:?set ALLOY_IMAGE}' "${PROXY_COMPOSE}" \
  || note "proxy Compose no longer requires explicit Alloy image selection"

# (h) dev and runtime compose reference the SAME healthcheck script.
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
