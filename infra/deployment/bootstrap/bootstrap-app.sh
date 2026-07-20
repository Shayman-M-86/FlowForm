#!/usr/bin/env bash
set -Eeuo pipefail

# FlowForm PRIVATE APP host bootstrap.
#
# Runs from cloud-init / EC2 user-data on first boot AND is re-run on every
# deploy. Idempotent: re-running re-materialises secrets, re-swaps the env
# file, and restarts Compose cleanly. It brings the private app box from a
# clean OS to a running backend behind the forced-egress proxy.
#
# What it does, in order:
#   1. Establish forced-proxy egress for this script's own AWS calls and for
#      the Docker daemon (HTTP(S)_PROXY -> Squid on the proxy box).
#   2. Materialise Secrets Manager values into tmpfs secret files (0600).
#   3. Render /opt/flowform/backend.env from SSM /flowform/<scope>/backend/*.
#   4. docker compose up the app stack.
#
# The ONLY prod-vs-rehearsal seam is BOOTSTRAP_ENDPOINT_URL: unset -> real
# AWS; set (rehearsal) -> LocalStack reached through the same proxy. Every
# other line is identical between rehearsal and production.
#
# Required environment (from user-data / deploy caller):
#   FLOWFORM_SCOPE          security scope namespace, e.g. "nonprod" | "prod"
#   PROXY_PRIVATE_IP        private IP of the proxy box running Squid :3128
#   APP_PRIVATE_IP          this host's private IP (compose binds backend here)
#   AWS_REGION              e.g. ap-southeast-2
# Optional:
#   BACKEND_IMAGE           overrides the image ref in backend.env (rehearsal
#                           points this at the local registry)
#   BOOTSTRAP_ENDPOINT_URL  AWS endpoint override (rehearsal: LocalStack)
#   COMPOSE_FILE            defaults to the repo's docker-compose.app.yml
#   FLOWFORM_SECRET_DIR     defaults to /run/flowform/secrets (tmpfs)
#   BOOTSTRAP_DRY_RUN=1     print intended actions + file perms, change nothing
#
# Exit codes: non-zero on any failure (fail closed — never leave a half-booted
# host that looks healthy).

log()  { printf '[bootstrap-app %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die()  { printf '[bootstrap-app %s] ERROR: %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; exit 1; }

DRY_RUN="${BOOTSTRAP_DRY_RUN:-0}"

# ---------------------------------------------------------------------------
# 0. Inputs
# ---------------------------------------------------------------------------
: "${FLOWFORM_SCOPE:?set FLOWFORM_SCOPE (e.g. nonprod)}"
: "${PROXY_PRIVATE_IP:?set PROXY_PRIVATE_IP (Squid host)}"
: "${APP_PRIVATE_IP:?set APP_PRIVATE_IP}"
: "${AWS_REGION:?set AWS_REGION}"

SECRET_DIR="${FLOWFORM_SECRET_DIR:-/run/flowform/secrets}"
BACKEND_ENV="/opt/flowform/backend.env"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# infra/deployment/bootstrap -> repo root is three up.
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/infra/containers/runtime/compose/app.yml}"
# Optional override compose file (rehearsal). Layered on with a second -f below.
# Empty in prod, so behaviour is exactly the single-file case. Prod-safe seam,
# like BOOTSTRAP_ENDPOINT_URL.
COMPOSE_OVERRIDE_FILE="${COMPOSE_OVERRIDE_FILE:-}"
COMPOSE_FORCE_RECREATE="${COMPOSE_FORCE_RECREATE:-0}"
[[ "${COMPOSE_FORCE_RECREATE}" == "0" || "${COMPOSE_FORCE_RECREATE}" == "1" ]] \
  || die "COMPOSE_FORCE_RECREATE must be 0 or 1"

# AWS CLI endpoint override is the sole rehearsal seam.
AWS_ARGS=(--region "${AWS_REGION}")
if [[ -n "${BOOTSTRAP_ENDPOINT_URL:-}" ]]; then
  AWS_ARGS+=(--endpoint-url "${BOOTSTRAP_ENDPOINT_URL}")
  log "using AWS endpoint override: ${BOOTSTRAP_ENDPOINT_URL} (rehearsal mode)"
fi

# shellcheck source=aws-cli-retry.sh
source "${SCRIPT_DIR}/aws-cli-retry.sh"

# ---------------------------------------------------------------------------
# 1. Forced-proxy egress
# ---------------------------------------------------------------------------
# CAUTION (mirrors docker-compose.app.yml): Python/boto3 IGNORE CIDR entries in
# NO_PROXY. Use hostnames/suffixes for anything this shell's AWS CLI must dial
# directly. IMDS (169.254.169.254) must never traverse Squid or instance-role
# credential lookups break.
export HTTP_PROXY="http://${PROXY_PRIVATE_IP}:3128"
export HTTPS_PROXY="http://${PROXY_PRIVATE_IP}:3128"
export NO_PROXY="localhost,127.0.0.1,169.254.169.254,.rds.amazonaws.com"
# Some tools read the lowercase spellings only.
export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" no_proxy="${NO_PROXY}"

configure_docker_daemon_proxy() {
  local drop_in_dir="/etc/systemd/system/docker.service.d"
  local drop_in="${drop_in_dir}/http-proxy.conf"
  # No CIDR exemptions: the daemon is Go, and Go's NO_PROXY matches CIDRs ONLY
  # against IP-literal request hosts — never resolved hostnames. The daemon only
  # ever dials hostnames (the registry/ECR host, S3 layer hosts), so image pulls
  # and pushes traverse the proxy exactly as prod's ECR-over-HTTPS pulls do. The
  # hostname-suffix exemptions below keep RDS and the S3 gateway path direct;
  # IMDS + localhost stay direct; the proxy is dialed AS the proxy, not exempted.
  local content
  content="$(cat <<EOF
[Service]
Environment="HTTP_PROXY=http://${PROXY_PRIVATE_IP}:3128"
Environment="HTTPS_PROXY=http://${PROXY_PRIVATE_IP}:3128"
Environment="NO_PROXY=localhost,127.0.0.1,169.254.169.254,.rds.amazonaws.com,.s3.${AWS_REGION}.amazonaws.com"
EOF
)"
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY_RUN: would write ${drop_in} (0644 root) and restart docker:"
    printf '%s\n' "${content}" | sed 's/^/    /'
    return
  fi
  install -d -m 0755 "${drop_in_dir}"
  printf '%s\n' "${content}" > "${drop_in}"
  chmod 0644 "${drop_in}"
  systemctl daemon-reload
  systemctl restart docker
  log "docker daemon proxy drop-in written and daemon restarted"
}

# ---------------------------------------------------------------------------
# 2. tmpfs secrets  (reuses the JSON-key + umask pattern from
#    scripts/secrets/fetch-dev-secrets.sh)
# ---------------------------------------------------------------------------
# secret file name  <-  (secret id suffix, json key)
#   FLOWFORM_APP_SECRET_KEY        <- app-secrets / app_secret_key
#   FLOWFORM_AUTH0_MGMT_SECRET     <- app-secrets / auth0_mgmt_secret
#   DATABASE_CORE_APP_PASSWORD     <- db-secrets  / db_core_app_password
#   DATABASE_RESPONSE_APP_PASSWORD <- db-secrets  / db_response_app_password
fetch_secret_string() { # $1 = secret id suffix (e.g. app-secrets)
  aws_cli_retry "Secrets Manager secret flowform/${FLOWFORM_SCOPE}/$1" \
    secretsmanager get-secret-value \
    --secret-id "flowform/${FLOWFORM_SCOPE}/$1" \
    --query SecretString --output text
}

extract_key() { # $1 = json blob  $2 = json key
  python3 -c '
import json, sys
value = json.loads(sys.argv[1]).get(sys.argv[2], "")
if not value:
    raise SystemExit(f"error: empty/missing key {sys.argv[2]!r}")
sys.stdout.write(value)
' "$1" "$2"
}

materialise_secrets() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY_RUN: would mount tmpfs at ${SECRET_DIR} (0700) and write 4 secret files (0600):"
    log "    FLOWFORM_APP_SECRET_KEY, FLOWFORM_AUTH0_MGMT_SECRET, DATABASE_CORE_APP_PASSWORD, DATABASE_RESPONSE_APP_PASSWORD"
    return
  fi

  # Mount a dedicated tmpfs so secret material is memory-backed and never
  # rests on EBS. Idempotent: skip if already tmpfs.
  install -d -m 0700 "${SECRET_DIR}"
  if ! findmnt -t tmpfs --target "${SECRET_DIR}" >/dev/null 2>&1; then
    mount -t tmpfs -o size=8m,mode=0700 tmpfs "${SECRET_DIR}"
  fi
  chmod 0700 "${SECRET_DIR}"

  local app_json db_json
  app_json="$(fetch_secret_string app-secrets)"
  db_json="$(fetch_secret_string db-secrets)"

  umask 177  # -> files 0600
  extract_key "${app_json}" app_secret_key         > "${SECRET_DIR}/FLOWFORM_APP_SECRET_KEY.secret.txt"
  extract_key "${app_json}" auth0_mgmt_secret      > "${SECRET_DIR}/FLOWFORM_AUTH0_MGMT_SECRET.secret.txt"
  extract_key "${db_json}"  db_core_app_password   > "${SECRET_DIR}/DATABASE_CORE_APP_PASSWORD.secret.txt"
  extract_key "${db_json}"  db_response_app_password > "${SECRET_DIR}/DATABASE_RESPONSE_APP_PASSWORD.secret.txt"
  umask 022
  log "materialised 4 secret files under ${SECRET_DIR} (0600)"
}

# ---------------------------------------------------------------------------
# 3. backend.env from SSM  (validate-to-tmp-then-mv, like
#    scripts/secrets/generate-env-files.sh)
# ---------------------------------------------------------------------------
render_backend_env() {
  local param_path="/flowform/${FLOWFORM_SCOPE}/backend/"

  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY_RUN: would render ${BACKEND_ENV} (0600 root) from SSM path ${param_path} plus injected APP/PROXY IPs"
    return
  fi

  install -d -m 0755 "$(dirname "${BACKEND_ENV}")"
  local tmp
  tmp="$(mktemp "${BACKEND_ENV}.tmp.XXXXXX")"
  chmod 0600 "${tmp}"
  # shellcheck disable=SC2064
  trap "rm -f '${tmp}'" RETURN

  # Each SSM param under the path becomes KEY=value, KEY = last path segment
  # upper-cased is NOT assumed — params are stored already named as the env
  # keys the backend expects (the CDK backend-param milestone owns that).
  local raw
  raw="$(aws_cli_retry "SSM path ${param_path}" ssm get-parameters-by-path \
    --path "${param_path}" --recursive --with-decryption \
    --query 'Parameters[].[Name,Value]' --output text)" \
    || die "SSM get-parameters-by-path ${param_path} failed"

  [[ -n "${raw}" ]] || die "no SSM parameters under ${param_path} — seed them first"

  # Name is the full path; the last segment is the env var name.
  printf '%s\n' "${raw}" | while IFS=$'\t' read -r name value; do
    [[ -n "${name}" ]] || continue
    printf '%s=%s\n' "${name##*/}" "${value}" >> "${tmp}"
  done

  # Inject values only the host knows (not in SSM): its own and the proxy IP,
  # and the image ref if the caller overrode it.
  {
    printf 'APP_PRIVATE_IP=%s\n'  "${APP_PRIVATE_IP}"
    printf 'PROXY_PRIVATE_IP=%s\n' "${PROXY_PRIVATE_IP}"
    printf 'HTTP_PROXY=http://%s:3128\n'  "${PROXY_PRIVATE_IP}"
    printf 'HTTPS_PROXY=http://%s:3128\n' "${PROXY_PRIVATE_IP}"
    printf 'NO_PROXY=%s\n' "${NO_PROXY}"
    [[ -n "${BACKEND_IMAGE:-}" ]] && printf 'BACKEND_IMAGE=%s\n' "${BACKEND_IMAGE}"
  } >> "${tmp}"

  # Validate: must define at least BACKEND_IMAGE (from SSM or override) or
  # compose interpolation fails closed.
  grep -q '^BACKEND_IMAGE=' "${tmp}" || die "backend.env has no BACKEND_IMAGE (not in SSM and no override)"

  mv "${tmp}" "${BACKEND_ENV}"
  chmod 0600 "${BACKEND_ENV}"
  trap - RETURN
  log "rendered ${BACKEND_ENV} (0600) from ${param_path}"
}

# ---------------------------------------------------------------------------
# 4. Compose up
# ---------------------------------------------------------------------------
compose_up() {
  [[ -f "${COMPOSE_FILE}" ]] || die "compose file not found: ${COMPOSE_FILE}"
  # Base compose, plus an optional override with a second -f (prod leaves
  # COMPOSE_OVERRIDE_FILE empty → exactly the single-file case).
  local compose_args=(-f "${COMPOSE_FILE}")
  if [[ -n "${COMPOSE_OVERRIDE_FILE}" ]]; then
    [[ -f "${COMPOSE_OVERRIDE_FILE}" ]] || die "compose override not found: ${COMPOSE_OVERRIDE_FILE}"
    compose_args+=(-f "${COMPOSE_OVERRIDE_FILE}")
  fi
  local up_args=(up -d)
  if [[ "${COMPOSE_FORCE_RECREATE}" == "1" ]]; then
    up_args+=(--force-recreate)
  fi
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY_RUN: would run: docker compose --env-file ${BACKEND_ENV} ${compose_args[*]} ${up_args[*]}"
    return
  fi
  FLOWFORM_SECRET_DIR="${SECRET_DIR}" \
    docker compose --env-file "${BACKEND_ENV}" "${compose_args[@]}" "${up_args[@]}"
  log "app compose stack started"
}

main() {
  log "scope=${FLOWFORM_SCOPE} app=${APP_PRIVATE_IP} proxy=${PROXY_PRIVATE_IP} dry_run=${DRY_RUN}"
  configure_docker_daemon_proxy
  materialise_secrets
  render_backend_env
  compose_up
  log "done"
}

main "$@"
