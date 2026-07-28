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
#   2. Render /opt/flowform/backend.env from SSM /flowform/<scope>/backend/*.
#   3. Materialise common Secrets Manager values into tmpfs secret files
#      (0600), plus database passwords only for the rehearsal password strategy.
#   4. Pull the backend image (with backoff), then docker compose up the stack.
#      The pull retries so a not-yet-published image is a wait, not a failure:
#      in prod the image is already in ECR (first attempt succeeds); in the
#      rehearsal the registry starts empty until the operator's push lands.
#
# FLOWFORM_DEPLOYMENT_TARGET selects the narrow credential strategy while the
# orchestration remains shared:
#   aws       -> both databases must use IAM; no DB password is fetched/mounted.
#   rehearsal -> both databases must use passwords from LocalStack db-secrets.
# Endpoint and Compose overrides remain transport/runtime seams, not implicit
# environment detection.
#
# Required environment (from user-data / deploy caller):
#   FLOWFORM_DEPLOYMENT_TARGET "aws" | "rehearsal"
#   FLOWFORM_SCOPE          security scope namespace, e.g. "nonprod" | "prod"
#   PROXY_PRIVATE_IP        private IP of the proxy box running Squid :3128
#   APP_PRIVATE_IP          this host's private IP (compose binds backend here)
#   AWS_REGION              e.g. ap-southeast-2
# Optional:
#   BACKEND_IMAGE           overrides the image ref in backend.env (rehearsal
#                           points this at the local registry)
#   ALLOY_IMAGE             overrides the Alloy image ref in backend.env
#   BOOTSTRAP_ENDPOINT_URL  AWS endpoint override (rehearsal: LocalStack)
#   COMPOSE_FILE            defaults to the repo's docker-compose.app.yml
#   FLOWFORM_SECRET_DIR     defaults to /run/flowform/secrets (tmpfs)
#   BOOTSTRAP_SSM_AGENT_OVERRIDE
#                           test seam for the AWS SSM Agent systemd drop-in
#   BOOTSTRAP_DRY_RUN=1     print intended actions + file perms, change nothing
#   BOOTSTRAP_IMAGE_PULL_MAX_ATTEMPTS         image-pull retries (default 60)
#   BOOTSTRAP_IMAGE_PULL_RETRY_DELAY_SECONDS  delay between them (default 5)
#
# Exit codes: non-zero on any failure (fail closed — never leave a half-booted
# host that looks healthy).

# Shared library provides log/die (as info/fatal aliases), the ERR trap, the
# flock guard, timeouts, the hardened retry helpers, compose validation, the
# local liveness probe, and non-secret failure diagnostics. BOOTSTRAP_NAME must
# be set before sourcing so every log line is tagged. aws-cli-retry.sh is a shim
# that pulls in the same common library (sourced below after AWS_ARGS is built).
BOOTSTRAP_NAME="bootstrap-app"

DRY_RUN="${BOOTSTRAP_DRY_RUN:-0}"
PREPARE_ONLY="${BOOTSTRAP_PREPARE_ONLY:-0}"
[[ "${PREPARE_ONLY}" == "0" || "${PREPARE_ONLY}" == "1" ]] \
  || { printf 'BOOTSTRAP_PREPARE_ONLY must be 0 or 1\n' >&2; exit 1; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# infra/deployment/bootstrap -> repo root is three up.
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# Pull in the shared library (log/die aliases, ERR trap, lock, timeouts, retry,
# compose_validate, wait_for_http, diagnostics) before any log/die call. The
# aws-cli-retry.sh shim re-sources the same common file; keep it for the baked
# cloud-init path that references it by name.
# shellcheck source=bootstrap-common.sh
source "${SCRIPT_DIR}/bootstrap-common.sh"
install_err_trap

# ---------------------------------------------------------------------------
# 0. Inputs
# ---------------------------------------------------------------------------
: "${FLOWFORM_SCOPE:?set FLOWFORM_SCOPE (e.g. nonprod)}"
: "${FLOWFORM_DEPLOYMENT_TARGET:?set FLOWFORM_DEPLOYMENT_TARGET (aws or rehearsal)}"
: "${PROXY_PRIVATE_IP:?set PROXY_PRIVATE_IP (Squid host)}"
: "${APP_PRIVATE_IP:?set APP_PRIVATE_IP}"
: "${AWS_REGION:?set AWS_REGION}"

case "${FLOWFORM_DEPLOYMENT_TARGET}" in
  aws|rehearsal) ;;
  *) die "FLOWFORM_DEPLOYMENT_TARGET must be 'aws' or 'rehearsal'" ;;
esac

SECRET_DIR="${FLOWFORM_SECRET_DIR:-/run/flowform/secrets}"
BACKEND_ENV="${BOOTSTRAP_BACKEND_ENV:-/opt/flowform/backend.env}"
DATABASE_AUTH_STRATEGY=""

COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/infra/containers/runtime/compose/app.yml}"
# Optional override compose file (rehearsal). Layered on with a second -f below.
# Empty for AWS, so behaviour is exactly the single-file case.
COMPOSE_OVERRIDE_FILE="${COMPOSE_OVERRIDE_FILE:-}"
COMPOSE_FORCE_RECREATE="${COMPOSE_FORCE_RECREATE:-0}"
[[ "${COMPOSE_FORCE_RECREATE}" == "0" || "${COMPOSE_FORCE_RECREATE}" == "1" ]] \
  || die "COMPOSE_FORCE_RECREATE must be 0 or 1"

# AWS_ARGS is consumed by aws_cli_retry (from the common library, already
# sourced above). Rehearsal normally supplies per-service endpoint variables;
# the global override remains available for callers such as the DB bootstrap.
AWS_ARGS=(--region "${AWS_REGION}")
if [[ -n "${BOOTSTRAP_ENDPOINT_URL:-}" ]]; then
  AWS_ARGS+=(--endpoint-url "${BOOTSTRAP_ENDPOINT_URL}")
  log "using AWS endpoint override: ${BOOTSTRAP_ENDPOINT_URL}"
fi

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

configure_ssm_agent_proxy() {
  if [[ "${FLOWFORM_DEPLOYMENT_TARGET}" != "aws" ]]; then
    log "SSM Agent proxy configuration is not required for ${FLOWFORM_DEPLOYMENT_TARGET}"
    return
  fi

  local drop_in="${BOOTSTRAP_SSM_AGENT_OVERRIDE:-/etc/systemd/system/amazon-ssm-agent.service.d/override.conf}"
  local drop_in_dir
  drop_in_dir="$(dirname "${drop_in}")"
  local content
  content="$(cat <<EOF
[Service]
Environment="http_proxy=http://${PROXY_PRIVATE_IP}:3128"
Environment="https_proxy=http://${PROXY_PRIVATE_IP}:3128"
Environment="no_proxy=169.254.169.254"
EOF
)"

  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY_RUN: would write ${drop_in} (0644 root) and restart amazon-ssm-agent only if required:"
    printf '%s\n' "${content}" | sed 's/^/    /'
    return
  fi

  install -d -m 0755 "${drop_in_dir}"
  if write_file_if_changed "${drop_in}" 0644 "${content}"; then
    systemctl daemon-reload
    systemctl restart amazon-ssm-agent
    systemctl is-active --quiet amazon-ssm-agent \
      || fatal "amazon-ssm-agent did not return to an active state after proxy configuration"
    log "SSM Agent proxy drop-in changed; agent restarted"
  elif systemctl is-active --quiet amazon-ssm-agent; then
    log "SSM Agent proxy drop-in unchanged; agent already active"
  else
    systemctl restart amazon-ssm-agent
    systemctl is-active --quiet amazon-ssm-agent \
      || fatal "amazon-ssm-agent did not return to an active state"
    log "SSM Agent proxy drop-in unchanged; inactive agent restarted"
  fi
}

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
    log "DRY_RUN: would write ${drop_in} (0644 root) and restart docker only if changed:"
    printf '%s\n' "${content}" | sed 's/^/    /'
    return
  fi
  install -d -m 0755 "${drop_in_dir}"
  # Only reload + restart Docker when the drop-in actually changed. An
  # unconditional restart on every deploy needlessly interrupts running
  # containers (and, on the app box, kills the very backend we are converging).
  if write_file_if_changed "${drop_in}" 0644 "${content}"; then
    systemctl daemon-reload
    systemctl restart docker
    systemctl is-active --quiet docker || fatal "docker did not return to an active state after restart"
    log "docker daemon proxy drop-in changed; daemon restarted"
  else
    log "docker daemon proxy drop-in unchanged; no restart"
  fi
}

# ---------------------------------------------------------------------------
# 2. backend.env from SSM  (validate-to-tmp-then-mv, like
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

  # Each SSM param under the path becomes KEY=value; KEY is the parameter's last
  # path segment (params are stored already named as the env keys the backend
  # expects — the CDK backend-param milestone owns that). Fetch JSON, not text:
  # jq derives + validates each name and rejects multiline values, avoiding the
  # tab/newline/whitespace footgun of --output text + IFS splitting.
  local raw
  raw="$(aws_cli_retry "SSM path ${param_path}" ssm get-parameters-by-path \
    --path "${param_path}" --recursive --with-decryption \
    --output json)" \
    || die "SSM get-parameters-by-path ${param_path} failed"

  printf '%s' "${raw}" | jq -e '.Parameters | length > 0' >/dev/null 2>&1 \
    || die "no SSM parameters under ${param_path} — seed them first"

  printf '%s' "${raw}" | render_ssm_path_to_env "${tmp}" \
    || die "failed to render SSM parameters under ${param_path} into ${BACKEND_ENV}"

  # Inject values only the host knows (not in SSM): its own and the proxy IP,
  # and image refs if the caller overrode them.
  {
    printf 'APP_PRIVATE_IP=%s\n'  "${APP_PRIVATE_IP}"
    printf 'PROXY_PRIVATE_IP=%s\n' "${PROXY_PRIVATE_IP}"
    printf 'HTTP_PROXY=http://%s:3128\n'  "${PROXY_PRIVATE_IP}"
    printf 'HTTPS_PROXY=http://%s:3128\n' "${PROXY_PRIVATE_IP}"
    printf 'NO_PROXY=%s\n' "${NO_PROXY}"
    [[ -n "${BACKEND_IMAGE:-}" ]] && printf 'BACKEND_IMAGE=%s\n' "${BACKEND_IMAGE}"
    [[ -n "${ALLOY_IMAGE:-}" ]] && printf 'ALLOY_IMAGE=%s\n' "${ALLOY_IMAGE}"
  } >> "${tmp}"

  # Validate image and database-auth inputs before any secret is fetched or
  # Compose interpolation begins. The .+ guards against present-but-empty values.
  grep -Eq '^BACKEND_IMAGE=.+$' "${tmp}" || die "backend.env has no non-empty BACKEND_IMAGE (not in SSM and no override)"
  grep -Eq '^ALLOY_IMAGE=.+$' "${tmp}" || die "backend.env has no non-empty ALLOY_IMAGE (not in SSM and no override)"
  grep -Eq '^DATABASE_CORE_AUTH_MODE=(password|iam)$' "${tmp}" \
    || die "backend.env must set DATABASE_CORE_AUTH_MODE to password or iam"
  grep -Eq '^DATABASE_RESPONSE_AUTH_MODE=(password|iam)$' "${tmp}" \
    || die "backend.env must set DATABASE_RESPONSE_AUTH_MODE to password or iam"

  mv "${tmp}" "${BACKEND_ENV}"
  chmod 0600 "${BACKEND_ENV}"
  trap - RETURN
  log "rendered ${BACKEND_ENV} (0600) from ${param_path}"
}

backend_env_value() { # $1 = exact environment key
  local key="$1" value
  value="$(awk -v key="${key}" '
    index($0, key "=") == 1 {
      count += 1
      value = substr($0, length(key) + 2)
    }
    END {
      if (count != 1) exit 1
      printf "%s", value
    }
  ' "${BACKEND_ENV}")" \
    || die "${BACKEND_ENV} must contain exactly one ${key} assignment"
  printf '%s' "${value}"
}

validate_database_auth_strategy() {
  local expected core_mode response_mode
  case "${FLOWFORM_DEPLOYMENT_TARGET}" in
    aws) expected="iam" ;;
    rehearsal) expected="password" ;;
  esac

  if [[ "${DRY_RUN}" == "1" ]]; then
    DATABASE_AUTH_STRATEGY="${expected}"
    log "DRY_RUN: ${FLOWFORM_DEPLOYMENT_TARGET} target requires both database auth modes to be ${expected}"
    return
  fi

  core_mode="$(backend_env_value DATABASE_CORE_AUTH_MODE)"
  response_mode="$(backend_env_value DATABASE_RESPONSE_AUTH_MODE)"
  [[ "${core_mode}" == "${expected}" ]] \
    || die "DATABASE_CORE_AUTH_MODE must be '${expected}' for deployment target '${FLOWFORM_DEPLOYMENT_TARGET}'"
  [[ "${response_mode}" == "${expected}" ]] \
    || die "DATABASE_RESPONSE_AUTH_MODE must be '${expected}' for deployment target '${FLOWFORM_DEPLOYMENT_TARGET}'"

  DATABASE_AUTH_STRATEGY="${expected}"
  log "database credential strategy validated: target=${FLOWFORM_DEPLOYMENT_TARGET} auth=${DATABASE_AUTH_STRATEGY}"
}

# ---------------------------------------------------------------------------
# 3. tmpfs secrets  (reuses the JSON-key + umask pattern from
#    scripts/secrets/fetch-dev-secrets.sh)
# ---------------------------------------------------------------------------
# secret file name  <-  (secret id suffix, json key)
#   FLOWFORM_APP_SECRET_KEY        <- app-secrets / app_secret_key
#   FLOWFORM_AUTH0_MGMT_SECRET     <- app-secrets / auth0_mgmt_secret
#   DATABASE_CORE_APP_PASSWORD     <- db-secrets  / db_core_app_password
#   DATABASE_RESPONSE_APP_PASSWORD <- db-secrets  / db_response_app_password
fetch_secret_string() { # $1 = secret id suffix (e.g. app-secrets)
  local secret_id="flowform/${FLOWFORM_SCOPE}/$1" output
  output="$(aws_cli_retry "Secrets Manager secret ${secret_id}" \
    secretsmanager get-secret-value \
    --secret-id "${secret_id}" \
    --query SecretString --output text)" \
    || die "could not read required secret ${secret_id}. $(secret_recovery_guidance)"
  [[ -n "${output}" && "${output}" != None ]] \
    || die "required secret ${secret_id} returned an empty SecretString. $(secret_recovery_guidance)"
  printf '%s' "${output}"
}

# Extract one key from a secret JSON object WITHOUT ever placing the secret on
# argv: the JSON blob is fed on stdin, and only the (non-secret) key name is an
# argument. This keeps secret material out of the process table and any
# argv-logging shim. Callers feed the blob in on stdin (see write_secret_key).
extract_key() { # $1 = json key ; JSON object on stdin
  # jq is provisioned into every image by install-base.sh (python3 is not on
  # minimal AL2023). The empty-value guard makes a missing/blank key fail the
  # boot instead of writing an empty secret file. -j: no trailing newline.
  jq -je --arg k "$1" '.[$k] // "" | select(length > 0)' \
    || die "secret JSON is missing or has an empty value for key: $1. $(secret_recovery_guidance)"
}

# Feed the JSON blob to extract_key via a builtin printf into a pipe: printf is a
# bash builtin, so the blob never forks a process and never lands on any argv or
# in a here-string temp file. The extracted value is written to the given file.
write_secret_key() { # $1 = json blob  $2 = json key  $3 = out file
  printf '%s' "$1" | extract_key "$2" > "$3"
}

materialise_secrets() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    if [[ "${DATABASE_AUTH_STRATEGY}" == "password" ]]; then
      log "DRY_RUN: would mount tmpfs at ${SECRET_DIR} (0700) and write 4 secret files (0600):"
      log "    FLOWFORM_APP_SECRET_KEY, FLOWFORM_AUTH0_MGMT_SECRET, DATABASE_CORE_APP_PASSWORD, DATABASE_RESPONSE_APP_PASSWORD"
    else
      log "DRY_RUN: would mount tmpfs at ${SECRET_DIR} (0700), write 2 common secret files (0600), and remove stale DB password files"
      log "    FLOWFORM_APP_SECRET_KEY, FLOWFORM_AUTH0_MGMT_SECRET"
    fi
    return
  fi

  # Mount a dedicated tmpfs so secret material is memory-backed and never
  # rests on EBS. Idempotent: skip if already tmpfs.
  install -d -m 0700 "${SECRET_DIR}"
  if ! findmnt -t tmpfs --target "${SECRET_DIR}" >/dev/null 2>&1; then
    mount -t tmpfs -o size=8m,mode=0700 tmpfs "${SECRET_DIR}"
  fi
  chmod 0700 "${SECRET_DIR}"

  local app_json db_json=""
  app_json="$(fetch_secret_string app-secrets)"
  if [[ "${DATABASE_AUTH_STRATEGY}" == "password" ]]; then
    db_json="$(fetch_secret_string db-secrets)"
  fi

  # JSON blobs reach jq on stdin via write_secret_key's builtin-printf pipe —
  # never on argv, never in a here-string temp file — so no secret touches the
  # process table or disk outside the tmpfs target.
  umask 177  # -> files 0600
  write_secret_key "${app_json}" app_secret_key           "${SECRET_DIR}/FLOWFORM_APP_SECRET_KEY.secret.txt"
  write_secret_key "${app_json}" auth0_mgmt_secret        "${SECRET_DIR}/FLOWFORM_AUTH0_MGMT_SECRET.secret.txt"
  if [[ "${DATABASE_AUTH_STRATEGY}" == "password" ]]; then
    write_secret_key "${db_json}" db_core_app_password \
      "${SECRET_DIR}/DATABASE_CORE_APP_PASSWORD.secret.txt"
    write_secret_key "${db_json}" db_response_app_password \
      "${SECRET_DIR}/DATABASE_RESPONSE_APP_PASSWORD.secret.txt"
  else
    # A target can be reconverged on an already-running host. Remove only the two
    # exact obsolete credential files so IAM mode cannot silently inherit a
    # password left by an earlier configuration.
    rm -f -- \
      "${SECRET_DIR}/DATABASE_CORE_APP_PASSWORD.secret.txt" \
      "${SECRET_DIR}/DATABASE_RESPONSE_APP_PASSWORD.secret.txt"
  fi
  umask 022
  if [[ "${DATABASE_AUTH_STRATEGY}" == "password" ]]; then
    log "materialised 4 secret files under ${SECRET_DIR} (0600)"
  else
    log "materialised 2 common secret files under ${SECRET_DIR} (0600); database passwords absent for IAM"
  fi
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
  local health_timeout="${BOOTSTRAP_HEALTH_TIMEOUT_SECONDS:-180}"
  local up_args=(up -d --wait --wait-timeout "${health_timeout}")
  if [[ "${COMPOSE_FORCE_RECREATE}" == "1" ]]; then
    up_args+=(--force-recreate)
  fi
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY_RUN: would validate config, pull (with retry) then run: docker compose --env-file ${BACKEND_ENV} ${compose_args[*]} ${up_args[*]}"
    return
  fi

  # Validate the merged config (interpolation, YAML, override merge) BEFORE any
  # pull/up so a broken config never disturbs a running stack.
  FLOWFORM_SECRET_DIR="${SECRET_DIR}" compose_validate "${BACKEND_ENV}" "${compose_args[@]}"

  # Pull the backend image first, with backoff. In prod the image is already in
  # ECR so this succeeds on the first attempt and adds no latency. In the
  # rehearsal the registry starts EMPTY — the operator's push (via app VM 220)
  # lands shortly after the VMs come up — so a missing manifest is "not ready
  # yet", not a fatal error: we wait it out rather than hard-failing the boot.
  # Once the pull succeeds, `up --wait` starts the stack and blocks until the
  # containers report healthy (or the timeout trips).
  local pull_attempts="${BOOTSTRAP_IMAGE_PULL_MAX_ATTEMPTS:-60}"
  local pull_delay="${BOOTSTRAP_IMAGE_PULL_RETRY_DELAY_SECONDS:-5}"
  local pull_timeout="${BOOTSTRAP_IMAGE_PULL_ATTEMPT_TIMEOUT_SECONDS:-300}"
  FLOWFORM_SECRET_DIR="${SECRET_DIR}" \
    retry_with_backoff "backend image pull" "${pull_attempts}" "${pull_delay}" "${pull_timeout}" \
    docker compose --env-file "${BACKEND_ENV}" "${compose_args[@]}" pull >/dev/null \
    || die "backend image never became pullable after ${pull_attempts} attempts"

  if ! FLOWFORM_SECRET_DIR="${SECRET_DIR}" \
      docker compose --env-file "${BACKEND_ENV}" "${compose_args[@]}" "${up_args[@]}"; then
    collect_compose_diagnostics "${BACKEND_ENV}" "${compose_args[@]}"
    die "app compose stack did not become healthy within ${health_timeout}s"
  fi
  log "app compose stack started and healthy"

  # Local, same-host liveness probe of the backend's real HTTP health route.
  # Boot-race-resilient (INFO while waiting, ERROR only on final timeout).
  # Cross-VM checks (app via Squid, DB reachability) stay in `rehearsal verify`.
  wait_for_http "http://${APP_PRIVATE_IP}:5000/api/v1/system/health" \
    "${BOOTSTRAP_HTTP_PROBE_ATTEMPTS:-30}" "${BOOTSTRAP_HTTP_PROBE_DELAY_SECONDS:-2}" \
    "backend health endpoint"
}

main() {
  log "target=${FLOWFORM_DEPLOYMENT_TARGET} scope=${FLOWFORM_SCOPE} app=${APP_PRIVATE_IP} proxy=${PROXY_PRIVATE_IP} dry_run=${DRY_RUN}"

  begin_step "Waiting for proxy egress"
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY_RUN: would wait for Squid at ${PROXY_PRIVATE_IP}:3128 before external AWS calls"
  else
    wait_for_tcp "Squid proxy ${PROXY_PRIVATE_IP}:3128" "${PROXY_PRIVATE_IP}" 3128
  fi
  end_step

  begin_step "Validating configuration"
  check_common_requirements
  check_aws_requirements
  # A dry run changes nothing and may run on a dev box without Docker or the
  # /run/lock namespace, so skip the lock + docker checks there.
  if [[ "${DRY_RUN}" != "1" ]]; then
    check_docker_requirements
    acquire_lock "${BOOTSTRAP_NAME}"
  fi
  end_step

  begin_step "Configuring SSM Agent proxy egress"
  configure_ssm_agent_proxy
  end_step

  begin_step "Configuring Docker proxy egress"
  configure_docker_daemon_proxy
  end_step

  if [[ "${PREPARE_ONLY}" == "1" ]]; then
    info "Docker image-relay preparation completed; runtime convergence deferred"
    return 0
  fi

  begin_step "Rendering backend.env from SSM"
  render_backend_env
  end_step

  begin_step "Selecting database credential strategy"
  validate_database_auth_strategy
  end_step

  begin_step "Materialising secrets"
  materialise_secrets
  end_step

  begin_step "Authenticating private image registries"
  login_ecr_for_images "${BACKEND_ENV}" BACKEND_IMAGE ALLOY_IMAGE
  end_step

  begin_step "Starting application containers"
  compose_up
  end_step

  info "bootstrap completed successfully"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
