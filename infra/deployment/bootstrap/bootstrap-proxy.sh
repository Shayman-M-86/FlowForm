#!/usr/bin/env bash
set -Eeuo pipefail

# FlowForm PUBLIC PROXY host bootstrap.
#
# Runs from cloud-init / user-data and on deploy. The proxy box is the public
# entry point (Caddy: inbound TLS + reverse proxy to the private app box) AND
# the controlled egress gateway (Squid: domain allow-list). It holds NO app
# secrets — so this bootstrap only renders proxy.env from SSM and starts the
# proxy Compose stack. Deliberately smaller than bootstrap-app.sh.
#
# Unlike the app box, the proxy box HAS a normal internet route (it must reach
# ACME, Route 53, and ECR). It does not route its own traffic through Squid.
#
# Required environment (from user-data / deploy caller):
#   FLOWFORM_SCOPE          security scope namespace, e.g. "nonprod" | "prod"
#   PROXY_PRIVATE_IP        this host's private IP (Squid binds here)
#   APP_PRIVATE_IP          private app box IP (Caddy upstream; Squid src ACL)
#   AWS_REGION              e.g. ap-southeast-2
# Optional:
#   CADDY_IMAGE             overrides the image ref in proxy.env
#   API_DOMAIN              public API hostname (else must come from SSM)
#   BOOTSTRAP_ENDPOINT_URL  AWS endpoint override (rehearsal: LocalStack)
#   DB_BOOTSTRAP_PRIVATE_IP rehearsal DB host temporarily admitted to Squid;
#                           unset elsewhere, producing a loopback sentinel ACL
#   COMPOSE_FILE            defaults to the repo's docker-compose.proxy.yml
#   COMPOSE_OVERRIDE_FILE   optional extra compose file layered on top with a
#                           second -f (empty in prod; rehearsal uses it to swap
#                           the Caddy TLS + Squid allow-list configs). This is a
#                           prod-safe seam, like BOOTSTRAP_ENDPOINT_URL.
#   BOOTSTRAP_DRY_RUN=1     print intended actions, change nothing

# Shared library provides log/die (as info/fatal aliases), the ERR trap, the
# flock guard, timeouts, the hardened retry helpers, compose validation, and
# non-secret failure diagnostics. BOOTSTRAP_NAME tags every log line.
BOOTSTRAP_NAME="bootstrap-proxy"

DRY_RUN="${BOOTSTRAP_DRY_RUN:-0}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# Pull in the shared library before any log/die call.
# shellcheck source=bootstrap-common.sh
source "${SCRIPT_DIR}/bootstrap-common.sh"
install_err_trap

: "${FLOWFORM_SCOPE:?set FLOWFORM_SCOPE}"
: "${PROXY_PRIVATE_IP:?set PROXY_PRIVATE_IP}"
: "${APP_PRIVATE_IP:?set APP_PRIVATE_IP}"
: "${AWS_REGION:?set AWS_REGION}"

# tmpfs-backed secret dir for the proxy box. Only the Grafana Cloud token lives
# here (materialised from the observability-secrets Secrets Manager entry); the
# proxy holds no other secret. Kept OUT of proxy.env so the token is never an
# environment variable — Alloy reads it from this file via a Docker secret.
SECRET_DIR="${FLOWFORM_SECRET_DIR:-/run/flowform/secrets}"
GRAFANA_TOKEN_FILE="${SECRET_DIR}/GRAFANA_CLOUD_TOKEN.secret.txt"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/infra/containers/runtime/compose/proxy.yml}"
# Optional override compose file (rehearsal). Assembled into the -f list below.
COMPOSE_OVERRIDE_FILE="${COMPOSE_OVERRIDE_FILE:-}"
# Rendered proxy env-file consumed by docker compose --env-file.
PROXY_ENV="${PROXY_ENV:-/opt/flowform/proxy.env}"

# AWS_ARGS is consumed by aws_cli_retry (from the common library sourced above).
AWS_ARGS=(--region "${AWS_REGION}")
if [[ -n "${BOOTSTRAP_ENDPOINT_URL:-}" ]]; then
  AWS_ARGS+=(--endpoint-url "${BOOTSTRAP_ENDPOINT_URL}")
  log "using AWS endpoint override: ${BOOTSTRAP_ENDPOINT_URL} (rehearsal mode)"
fi

# Extract one key from a secret JSON object WITHOUT placing the secret on argv:
# the blob is fed on stdin (via the builtin-printf pipe below) and only the key
# name is an argument. jq is provisioned into every image by install-base.sh
# (python3 is not on minimal AL2023).
extract_key() { # $1 = json key ; JSON object on stdin
  jq -je --arg k "$1" '.[$k] // "" | select(length > 0)' \
    || die "observability secret JSON is missing or has an empty value for key: $1. $(secret_recovery_guidance)"
}

# The Grafana Cloud token is the proxy's only secret. Fetch the
# observability-secrets Secrets Manager entry and materialise the token into a
# tmpfs 0600 file that the alloy container mounts as a Docker secret. The value
# never enters proxy.env, the environment, or any argv.
materialise_observability_secret() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY_RUN: would mount tmpfs at ${SECRET_DIR} (0700) and write ${GRAFANA_TOKEN_FILE} (0600) from Secrets Manager observability-secrets"
    return
  fi

  install -d -m 0700 "${SECRET_DIR}"
  if ! findmnt -t tmpfs --target "${SECRET_DIR}" >/dev/null 2>&1; then
    mount -t tmpfs -o size=1m,mode=0700 tmpfs "${SECRET_DIR}"
  fi
  chmod 0700 "${SECRET_DIR}"

  local obs_json
  obs_json="$(aws_cli_retry "Secrets Manager observability secret" \
    secretsmanager get-secret-value \
    --secret-id "flowform/${FLOWFORM_SCOPE}/observability-secrets" \
    --query SecretString --output text)" \
    || die "could not fetch flowform/${FLOWFORM_SCOPE}/observability-secrets. $(secret_recovery_guidance)"
  [[ -n "${obs_json}" && "${obs_json}" != None ]] \
    || die "flowform/${FLOWFORM_SCOPE}/observability-secrets returned an empty SecretString. $(secret_recovery_guidance)"

  umask 177  # -> 0600
  # Builtin printf into the pipe: no fork, no argv exposure, no temp file.
  printf '%s' "${obs_json}" | extract_key grafana_cloud_token > "${GRAFANA_TOKEN_FILE}"
  umask 022
  log "materialised Grafana Cloud token into ${GRAFANA_TOKEN_FILE} (0600)"
}

render_proxy_env() {
  local param_path="/flowform/${FLOWFORM_SCOPE}/proxy/"

  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY_RUN: would render ${PROXY_ENV} (0644 root) from SSM ${param_path} plus injected IPs/CIDR"
    return
  fi

  install -d -m 0755 "$(dirname "${PROXY_ENV}")"
  local tmp
  tmp="$(mktemp "${PROXY_ENV}.tmp.XXXXXX")"
  chmod 0644 "${tmp}"
  # shellcheck disable=SC2064
  trap "rm -f '${tmp}'" RETURN

  # Proxy params are optional (API_DOMAIN/CADDY_IMAGE may come from the caller),
  # so an empty path is not fatal here — unlike the app box. Fetch JSON and let
  # render_ssm_path_to_env validate names + reject multiline values (kills the
  # tab/newline/whitespace footgun of --output text parsing).
  local raw
  raw="$(aws_cli_retry "SSM path ${param_path}" ssm get-parameters-by-path \
    --path "${param_path}" --recursive --with-decryption \
    --output json)" \
    || die "SSM get-parameters-by-path ${param_path} failed"

  if printf '%s' "${raw}" | jq -e '.Parameters | length > 0' >/dev/null 2>&1; then
    printf '%s' "${raw}" | render_ssm_path_to_env "${tmp}" \
      || die "failed to render SSM parameters under ${param_path} into ${PROXY_ENV}"
  fi

  # Host-known values (not in SSM). Squid source ACL is exactly this app IP.
  {
    printf 'PROXY_PRIVATE_IP=%s\n' "${PROXY_PRIVATE_IP}"
    printf 'APP_PRIVATE_IP=%s\n'   "${APP_PRIVATE_IP}"
    printf 'SQUID_APP_SOURCE_CIDR=%s/32\n' "${APP_PRIVATE_IP}"
    if [[ -n "${DB_BOOTSTRAP_PRIVATE_IP:-}" ]]; then
      printf 'SQUID_DB_BOOTSTRAP_SOURCE_CIDR=%s/32\n' "${DB_BOOTSTRAP_PRIVATE_IP}"
    else
      printf 'SQUID_DB_BOOTSTRAP_SOURCE_CIDR=127.0.0.1/32\n'
    fi
    printf 'AWS_REGION=%s\n' "${AWS_REGION}"
    [[ -n "${CADDY_IMAGE:-}" ]] && printf 'CADDY_IMAGE=%s\n' "${CADDY_IMAGE}"
    [[ -n "${API_DOMAIN:-}" ]]  && printf 'API_DOMAIN=%s\n'  "${API_DOMAIN}"
  } >> "${tmp}"

  # Require NON-EMPTY values (.+ guards against present-but-empty entries that a
  # bare prefix match would accept and that would break compose interpolation).
  grep -Eq '^CADDY_IMAGE=.+$' "${tmp}" || die "proxy.env has no non-empty CADDY_IMAGE (not in SSM and no override)"
  grep -Eq '^API_DOMAIN=.+$'  "${tmp}" || die "proxy.env has no non-empty API_DOMAIN (not in SSM and no override)"
  # API_DOMAIN must be a bare hostname (Caddy's site address + Route 53 record),
  # not a URL or arbitrary string. Reject anything with a scheme, path, or space.
  local api_domain
  api_domain="$(grep -E '^API_DOMAIN=' "${tmp}" | head -n1 | cut -d= -f2-)"
  [[ "${api_domain}" =~ ^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+$ ]] \
    || die "API_DOMAIN is not a valid hostname: ${api_domain}"

  mv "${tmp}" "${PROXY_ENV}"
  chmod 0644 "${PROXY_ENV}"
  trap - RETURN
  log "rendered ${PROXY_ENV}"
}

compose_up() {
  [[ -f "${COMPOSE_FILE}" ]] || die "compose file not found: ${COMPOSE_FILE}"
  # Base compose, plus an optional override layered on with a second -f (prod
  # leaves COMPOSE_OVERRIDE_FILE empty, so this is exactly the single-file case).
  local compose_args=(-f "${COMPOSE_FILE}")
  if [[ -n "${COMPOSE_OVERRIDE_FILE}" ]]; then
    [[ -f "${COMPOSE_OVERRIDE_FILE}" ]] || die "compose override not found: ${COMPOSE_OVERRIDE_FILE}"
    compose_args+=(-f "${COMPOSE_OVERRIDE_FILE}")
  fi
  local health_timeout="${BOOTSTRAP_HEALTH_TIMEOUT_SECONDS:-180}"
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY_RUN: would validate config then run: FLOWFORM_SECRET_DIR=${SECRET_DIR} docker compose --env-file ${PROXY_ENV} ${compose_args[*]} up -d --wait --wait-timeout ${health_timeout}"
    return
  fi

  # Validate the merged config before touching containers.
  FLOWFORM_SECRET_DIR="${SECRET_DIR}" compose_validate "${PROXY_ENV}" "${compose_args[@]}"

  # Export FLOWFORM_SECRET_DIR so the alloy service's file-backed Docker secret
  # resolves to the tmpfs token file materialised above. --wait blocks until the
  # containers report healthy. There is NO host-side HTTP probe here: Caddy's
  # admin (:2019) and Alloy's UI (:12345) are container-loopback / unpublished,
  # so the container healthchecks (via --wait) are the only reachable local
  # signal. Squid end-to-end reachability is verified from the workstation by
  # `rehearsal verify`, not from inside this bootstrap.
  if ! FLOWFORM_SECRET_DIR="${SECRET_DIR}" \
      docker compose --env-file "${PROXY_ENV}" "${compose_args[@]}" \
      up -d --wait --wait-timeout "${health_timeout}"; then
    collect_compose_diagnostics "${PROXY_ENV}" "${compose_args[@]}"
    die "proxy compose stack did not become healthy within ${health_timeout}s"
  fi
  log "proxy compose stack started and healthy"
}

main() {
  log "scope=${FLOWFORM_SCOPE} proxy=${PROXY_PRIVATE_IP} app=${APP_PRIVATE_IP} dry_run=${DRY_RUN}"

  begin_step "Validating configuration"
  check_common_requirements
  check_aws_requirements
  if [[ "${DRY_RUN}" != "1" ]]; then
    check_docker_requirements
    acquire_lock "${BOOTSTRAP_NAME}"
  fi
  end_step

  begin_step "Materialising observability secret"
  materialise_observability_secret
  end_step

  begin_step "Rendering proxy.env from SSM"
  render_proxy_env
  end_step

  begin_step "Starting proxy containers"
  compose_up
  end_step

  info "bootstrap completed successfully"
}

main "$@"
