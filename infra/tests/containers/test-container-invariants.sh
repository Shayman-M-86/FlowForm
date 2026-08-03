#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
FAIL=0

note() {
  printf 'FAIL: %s\n' "$*" >&2
  FAIL=1
}

require_file() {
  [[ -f "$1" ]] || note "missing file: ${1#${REPO_ROOT}/}"
}

IMAGE_ROOT="${REPO_ROOT}/infra/containers/images"
RUNTIME_ROOT="${REPO_ROOT}/infra/containers/runtime"
BACKEND="${IMAGE_ROOT}/backend/Dockerfile"
CADDY_DIR="${IMAGE_ROOT}/caddy"
SQUID_DIR="${IMAGE_ROOT}/squid"
ALLOY_DIR="${IMAGE_ROOT}/alloy"
APP_COMPOSE="${RUNTIME_ROOT}/aws/common/compose/app.yml"
PROXY_COMPOSE="${RUNTIME_ROOT}/aws/common/compose/proxy.yml"
LOAD_RELEASE_MANIFEST="${RUNTIME_ROOT}/common/scripts/load-release-manifest.sh"
RUN_ROLE="${RUNTIME_ROOT}/common/scripts/run-role.sh"
DEVELOPMENT_COMPOSE="${RUNTIME_ROOT}/development/compose/compose.yml"
REHEARSAL_ROOT="${RUNTIME_ROOT}/proxmox/rehearsal"
REHEARSAL_PROXY="${REHEARSAL_ROOT}/compose/proxy.override.yml"
MANIFEST="${REPO_ROOT}/infra/contracts/image-sources.json"
RUNTIME_PARAMETERS="${REPO_ROOT}/infra/contracts/runtime-parameters.json"

for file in \
  "${BACKEND}" \
  "${CADDY_DIR}/Dockerfile" \
  "${CADDY_DIR}/Caddyfile" \
  "${CADDY_DIR}/rate-limits.caddy" \
  "${SQUID_DIR}/Dockerfile" \
  "${SQUID_DIR}/squid.conf.template" \
  "${SQUID_DIR}/allowed-domains.txt" \
  "${SQUID_DIR}/entrypoint.sh" \
  "${SQUID_DIR}/healthcheck.sh" \
  "${ALLOY_DIR}/Dockerfile" \
  "${ALLOY_DIR}/entrypoint.sh" \
  "${ALLOY_DIR}/config/app.alloy" \
  "${ALLOY_DIR}/config/proxy.alloy" \
  "${APP_COMPOSE}" \
  "${PROXY_COMPOSE}" \
  "${LOAD_RELEASE_MANIFEST}" \
  "${RUN_ROLE}" \
  "${REHEARSAL_PROXY}" \
  "${MANIFEST}" \
  "${RUNTIME_PARAMETERS}"; do
  require_file "${file}"
done

for executable in \
  "${SQUID_DIR}/entrypoint.sh" \
  "${SQUID_DIR}/healthcheck.sh" \
  "${ALLOY_DIR}/entrypoint.sh" \
  "${LOAD_RELEASE_MANIFEST}" \
  "${RUN_ROLE}"; do
  [[ -x "${executable}" ]] || note "container script is not executable: ${executable#${REPO_ROOT}/}"
done

# Old ownership roots must not reappear. Images own immutable build inputs;
# runtime owns Compose topology and platform/environment adapters.
for obsolete in \
  "${REPO_ROOT}/infra/containers/backend" \
  "${REPO_ROOT}/infra/containers/caddy" \
  "${REPO_ROOT}/infra/containers/squid" \
  "${REPO_ROOT}/infra/containers/alloy" \
  "${REPO_ROOT}/infra/containers/runtime/services" \
  "${REPO_ROOT}/infra/containers/runtime/compose" \
  "${REPO_ROOT}/infra/containers/strategies" \
  "${REPO_ROOT}/infra/machine-images/app/compose" \
  "${REPO_ROOT}/infra/machine-images/proxy/compose"; do
  [[ ! -e "${obsolete}" ]] || note "obsolete container ownership path exists: ${obsolete#${REPO_ROOT}/}"
done

# Backend remains one pinned deployable image and owns its health probe.
grep -Eq '^FROM python:3\.14\.6-slim-trixie@sha256:[0-9a-f]{64}$' "${BACKEND}" \
  || note "Backend Python source is not immutable"
grep -Eq '^COPY --from=ghcr\.io/astral-sh/uv:0\.11\.31@sha256:[0-9a-f]{64} ' "${BACKEND}" \
  || note "Backend uv source is not immutable"
grep -Fq 'CMD ["python", "/app/scripts/healthcheck.py"]' "${BACKEND}" \
  || note "Backend image does not own its health probe"
grep -Fq 'https://truststore.pki.rds.amazonaws.com/ap-southeast-2/ap-southeast-2-bundle.pem' \
  "${BACKEND}" || note "Backend image does not install the regional RDS CA bundle"
grep -Fq 'sha256:d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b' \
  "${BACKEND}" || note "Backend RDS CA bundle is not checksum-pinned"
grep -Fq 'dockerfile: infra/containers/images/backend/Dockerfile' \
  "${DEVELOPMENT_COMPOSE}" \
  || note "development no longer builds the canonical Backend Dockerfile"
grep -Fq 'infra/containers/images/backend/Dockerfile' \
  "${REHEARSAL_ROOT}/services/registry/build-and-push-backend.sh" \
  || note "rehearsal no longer builds the canonical Backend Dockerfile"

# Caddy owns the Route 53 binary, production template, and health probe.
grep -Eq '^FROM caddy:2\.11\.4-builder-alpine@sha256:[0-9a-f]{64} AS builder$' \
  "${CADDY_DIR}/Dockerfile" || note "Caddy builder source is not immutable"
grep -Eq '^FROM caddy:2\.11\.4-alpine@sha256:[0-9a-f]{64}$' \
  "${CADDY_DIR}/Dockerfile" || note "Caddy runtime source is not immutable"
grep -Fq -- '--with github.com/caddy-dns/route53@v1.6.2' \
  "${CADDY_DIR}/Dockerfile" || note "Caddy Route 53 module is not pinned"
grep -Fq -- '--with github.com/mholt/caddy-ratelimit@5625512f24f6f59d6f64fb3aafe5eecff0b286db' \
  "${CADDY_DIR}/Dockerfile" || note "Caddy rate-limit module is not pinned"
grep -Fq 'COPY Caddyfile /etc/caddy/Caddyfile' "${CADDY_DIR}/Dockerfile" \
  || note "Caddy image does not embed its production Caddyfile"
grep -Fq 'COPY rate-limits.caddy /etc/caddy/rate-limits.caddy' \
  "${CADDY_DIR}/Dockerfile" || note "Caddy image does not embed its rate-limit configuration"
grep -Fq "grep -Fxq 'http.handlers.rate_limit'" "${CADDY_DIR}/Dockerfile" \
  || note "Caddy image does not verify its rate-limit module"
grep -Fq $'\t\tdns route53' "${CADDY_DIR}/Caddyfile" \
  || note "production Caddyfile does not use Route 53 DNS-01"
grep -Fq $'\t\tpropagation_delay 60s' "${CADDY_DIR}/Caddyfile" \
  || note "production Caddyfile does not wait for Route 53 propagation"
grep -Fq 'reverse_proxy http://{$APP_UPSTREAM_HOST}:5000' "${CADDY_DIR}/Caddyfile" \
  || note "Caddy does not use the stable app upstream host contract"
grep -Fq $'\timport rate-limits.caddy' "${CADDY_DIR}/Caddyfile" \
  || note "production Caddyfile does not import its rate-limit configuration"
grep -Fq $'\timport rate-limits.caddy' \
  "${REHEARSAL_ROOT}/services/caddy/Caddyfile.proxy" \
  || note "rehearsal Caddyfile does not import its rate-limit configuration"
for zone in general_api respondent_link_resolution account_bootstrap email_actions; do
  grep -Fq $'\tzone '"${zone}"' {' "${CADDY_DIR}/rate-limits.caddy" \
    || note "Caddy rate-limit configuration has no ${zone} zone"
done
grep -Fq '/api/v1/respondent/links/resolve' "${CADDY_DIR}/rate-limits.caddy" \
  || note "Caddy rate-limit configuration does not cover respondent link resolution"
grep -Fq '/api/v1/studio/projects/*/surveys/*/links/*/send-email' \
  "${CADDY_DIR}/rate-limits.caddy" \
  || note "Caddy rate-limit configuration does not cover survey-link email sending"

# AWS and rehearsal proxy behavior must differ only in certificate selection.
strip_caddy() {
  awk '
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*$/ { next }
    /^[[:space:]]*tls[[:space:]]/ { if ($0 ~ /\{[[:space:]]*$/) intls=1; next }
    intls && /^[[:space:]]*\}/ { intls=0; next }
    intls { next }
    { print }
  ' "$1"
}
if ! diff \
  <(strip_caddy "${CADDY_DIR}/Caddyfile") \
  <(strip_caddy "${REHEARSAL_ROOT}/services/caddy/Caddyfile.proxy") \
  >/dev/null; then
  note "production and rehearsal Caddy behavior differs beyond TLS"
fi

# Squid owns rendering, parsing, the AWS policy, and health behavior.
grep -Eq '^FROM ubuntu/squid:6\.6-24\.04_edge@sha256:[0-9a-f]{64}$' \
  "${SQUID_DIR}/Dockerfile" || note "Squid source is not immutable"
grep -Fq 'COPY squid.conf.template /etc/squid/squid.conf.template' \
  "${SQUID_DIR}/Dockerfile" || note "Squid image does not embed its template"
grep -Fq 'COPY allowed-domains.txt /etc/squid/allowed-domains.txt' \
  "${SQUID_DIR}/Dockerfile" || note "Squid image does not embed its AWS allow-list"
grep -Fq 'squid -k parse -f "${rendered}"' "${SQUID_DIR}/entrypoint.sh" \
  || note "Squid startup does not validate rendered configuration"
grep -Fq "'touch /var/log/squid/access.log' proxy" "${SQUID_DIR}/entrypoint.sh" \
  || note "Squid entrypoint does not create its access log as the proxy user"
if grep -Fq 'chown proxy:proxy /var/log/squid/access.log' "${SQUID_DIR}/entrypoint.sh"; then
  note "Squid entrypoint still requires the dropped CHOWN capability"
fi
grep -Fq 'access_log stdio:/var/log/squid/access.log flowform_access' \
  "${SQUID_DIR}/squid.conf.template" || note "Squid access logging contract changed"
for ssm_host in \
  ssm.ap-southeast-2.amazonaws.com \
  ssmmessages.ap-southeast-2.amazonaws.com \
  ec2messages.ap-southeast-2.amazonaws.com; do
  grep -Fxq "${ssm_host}" "${SQUID_DIR}/allowed-domains.txt" \
    || note "Squid AWS allow-list is missing ${ssm_host}"
done

# Alloy owns both role configs and selects exactly one at runtime.
grep -Fq 'COPY config/app.alloy /etc/flowform/alloy/app.alloy' \
  "${ALLOY_DIR}/Dockerfile" || note "Alloy image does not embed app config"
grep -Fq 'COPY config/proxy.alloy /etc/flowform/alloy/proxy.alloy' \
  "${ALLOY_DIR}/Dockerfile" || note "Alloy image does not embed proxy config"
grep -Fq 'FLOWFORM_ALLOY_ROLE' "${ALLOY_DIR}/entrypoint.sh" \
  || note "Alloy entrypoint does not require a role"
for config in "${ALLOY_DIR}/config/app.alloy" "${ALLOY_DIR}/config/proxy.alloy"; do
  grep -Fq 'sys.env("FLOWFORM_ENV")' "${config}" \
    || note "${config##*/} does not use runtime environment identity"
  grep -Fq 'sys.env("FLOWFORM_PLATFORM")' "${config}" \
    || note "${config##*/} does not use runtime platform identity"
  grep -Fq 'loki.source.journal "host"' "${config}" \
    || note "${config##*/} does not collect the host systemd journal"
  grep -Fq 'target_label  = "service_name"' "${config}" \
    || note "${config##*/} does not expose journal units as service names"
  grep -Fq 'source_labels = ["__journal_priority_keyword"]' "${config}" \
    || note "${config##*/} does not expose journal priority as log level"
done

# Backend records already arrive as valid JSON. Alloy may extract stable labels,
# but it must not replace the line with a partial logfmt rendering: doing so
# breaks Grafana `| json` queries and drops sanitized exception details.
backend_json_pipeline="$(
  awk '
    /selector = "\{service_name=\\"backend\\"\}"/ { in_backend = 1 }
    /This agent.s own logs/ { in_backend = 0 }
    in_backend { print }
  ' "${ALLOY_DIR}/config/app.alloy"
)"
[[ -n "${backend_json_pipeline}" ]] \
  || note "App Alloy config has no backend JSON processing stage"
if grep -Fq 'stage.output' <<<"${backend_json_pipeline}"; then
  note "App Alloy replaces the backend JSON line instead of retaining it"
fi
grep -Fq 'prevents query-time' "${ALLOY_DIR}/config/app.alloy" \
  || note "App Alloy does not document preservation of backend JSON diagnostics"

# Role Compose consumes container-owned defaults; only rehearsal may override
# the production Caddyfile and Squid allow-list.
if grep -Eq 'containers/(runtime/services|strategies/aws/services)' \
  "${APP_COMPOSE}" "${PROXY_COMPOSE}"; then
  note "role Compose still mounts legacy container service configuration"
fi
grep -Fq 'FLOWFORM_ALLOY_ROLE: app' "${APP_COMPOSE}" \
  || note "App Compose does not select the app Alloy role"
grep -Fq 'FLOWFORM_ALLOY_ROLE: proxy' "${PROXY_COMPOSE}" \
  || note "Proxy Compose does not select the proxy Alloy role"
grep -Fq 'operation=converge' "${RUN_ROLE}" \
  || note "role convergence does not emit an operation record"
grep -Fq '"${FLOWFORM_RELEASE_SOURCE_COMMIT}"' "${RUN_ROLE}" \
  || note "role convergence does not identify the selected source commit"
grep -Fq 'Caddyfile.proxy:/etc/caddy/Caddyfile:ro' "${REHEARSAL_PROXY}" \
  || note "rehearsal no longer overrides the production Caddyfile"
grep -Fq 'allowed-domains.txt:/etc/squid/allowed-domains.txt:ro' "${REHEARSAL_PROXY}" \
  || note "rehearsal no longer overrides the production Squid allow-list"

# Publication contract builds all deployable images from these canonical paths.
jq -e '
  .schema_version == 1
  and (.images | keys == ["alloy", "backend", "caddy", "squid"])
  and (.images | to_entries | all(.value.kind == "build"))
  and .images.backend.context == "."
  and .images.backend.dockerfile == "infra/containers/images/backend/Dockerfile"
  and .images.caddy.context == "infra/containers/images/caddy"
  and .images.caddy.dockerfile == "Dockerfile"
  and .images.squid.context == "infra/containers/images/squid"
  and .images.squid.dockerfile == "Dockerfile"
  and .images.alloy.context == "infra/containers/images/alloy"
  and .images.alloy.dockerfile == "Dockerfile"
' "${MANIFEST}" >/dev/null || note "image source contract does not target canonical build contexts"

# Role release manifests are the sole AWS source of immutable image references.
# Runtime configuration must not reintroduce per-image SSM parameters that
# render duplicate assignments into app.env or proxy.env.
jq -e '
  [
    .runtime_groups.backend.parameters[].name,
    .runtime_groups.proxy.parameters[].name
  ]
  | all(
      . != "BACKEND_IMAGE"
      and . != "CADDY_IMAGE"
      and . != "SQUID_IMAGE"
      and . != "ALLOY_IMAGE"
    )
' "${RUNTIME_PARAMETERS}" >/dev/null \
  || note "runtime parameter contract still owns role release image references"

if (( FAIL == 0 )); then
  printf '[test-container-invariants] PASS\n'
else
  printf '[test-container-invariants] FAIL\n' >&2
  exit 1
fi
