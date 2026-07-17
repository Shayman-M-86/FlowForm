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
#   COMPOSE_FILE            defaults to the repo's docker-compose.proxy.yml
#   COMPOSE_OVERRIDE_FILE   optional extra compose file layered on top with a
#                           second -f (empty in prod; rehearsal uses it to swap
#                           the Caddy TLS + Squid allow-list configs). This is a
#                           prod-safe seam, like BOOTSTRAP_ENDPOINT_URL.
#   BOOTSTRAP_DRY_RUN=1     print intended actions, change nothing

log() { printf '[bootstrap-proxy %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die() { printf '[bootstrap-proxy %s] ERROR: %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; exit 1; }

DRY_RUN="${BOOTSTRAP_DRY_RUN:-0}"

: "${FLOWFORM_SCOPE:?set FLOWFORM_SCOPE}"
: "${PROXY_PRIVATE_IP:?set PROXY_PRIVATE_IP}"
: "${APP_PRIVATE_IP:?set APP_PRIVATE_IP}"
: "${AWS_REGION:?set AWS_REGION}"

PROXY_ENV="/opt/flowform/proxy.env"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/infra/containers/deployment/compose/compose.proxy.yml}"
# Optional override compose file (rehearsal). Assembled into the -f list below.
COMPOSE_OVERRIDE_FILE="${COMPOSE_OVERRIDE_FILE:-}"

AWS_ARGS=(--region "${AWS_REGION}")
if [[ -n "${BOOTSTRAP_ENDPOINT_URL:-}" ]]; then
  AWS_ARGS+=(--endpoint-url "${BOOTSTRAP_ENDPOINT_URL}")
  log "using AWS endpoint override: ${BOOTSTRAP_ENDPOINT_URL} (rehearsal mode)"
fi

# shellcheck source=aws-cli-retry.sh
source "${SCRIPT_DIR}/aws-cli-retry.sh"

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
  # so an empty path is not fatal here — unlike the app box.
  local raw
  raw="$(aws_cli_retry "SSM path ${param_path}" ssm get-parameters-by-path \
    --path "${param_path}" --recursive --with-decryption \
    --query 'Parameters[].[Name,Value]' --output text)" \
    || die "SSM get-parameters-by-path ${param_path} failed"

  if [[ -n "${raw}" ]]; then
    printf '%s\n' "${raw}" | while IFS=$'\t' read -r name value; do
      [[ -n "${name}" ]] || continue
      printf '%s=%s\n' "${name##*/}" "${value}" >> "${tmp}"
    done
  fi

  # Host-known values (not in SSM). Squid source ACL is exactly this app IP.
  {
    printf 'PROXY_PRIVATE_IP=%s\n' "${PROXY_PRIVATE_IP}"
    printf 'APP_PRIVATE_IP=%s\n'   "${APP_PRIVATE_IP}"
    printf 'SQUID_APP_SOURCE_CIDR=%s/32\n' "${APP_PRIVATE_IP}"
    printf 'AWS_REGION=%s\n' "${AWS_REGION}"
    [[ -n "${CADDY_IMAGE:-}" ]] && printf 'CADDY_IMAGE=%s\n' "${CADDY_IMAGE}"
    [[ -n "${API_DOMAIN:-}" ]]  && printf 'API_DOMAIN=%s\n'  "${API_DOMAIN}"
  } >> "${tmp}"

  grep -q '^CADDY_IMAGE=' "${tmp}" || die "proxy.env has no CADDY_IMAGE (not in SSM and no override)"
  grep -q '^API_DOMAIN='  "${tmp}" || die "proxy.env has no API_DOMAIN (not in SSM and no override)"

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
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY_RUN: would run: docker compose --env-file ${PROXY_ENV} ${compose_args[*]} up -d"
    return
  fi
  docker compose --env-file "${PROXY_ENV}" "${compose_args[@]}" up -d
  log "proxy compose stack started"
}

main() {
  log "scope=${FLOWFORM_SCOPE} proxy=${PROXY_PRIVATE_IP} app=${APP_PRIVATE_IP} dry_run=${DRY_RUN}"
  render_proxy_env
  compose_up
  log "done"
}

main "$@"
