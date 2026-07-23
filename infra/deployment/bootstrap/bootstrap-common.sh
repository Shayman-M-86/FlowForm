#!/usr/bin/env bash

# Shared bootstrap library for FlowForm boot-time host scripts (app, proxy, db).
#
# Sourced by bootstrap-app.sh, bootstrap-proxy.sh, bootstrap-db.sh (and, for
# backward compatibility, by aws-cli-retry.sh which is now a thin shim). It owns
# the cross-cutting concerns so error output and behaviour are identical on
# Proxmox and on the future AWS deployment:
#
#   * structured logging + an ERR trap that reports step/function/line/exit code
#   * a single-instance flock guard
#   * require_command / prerequisite checks
#   * run_with_timeout + a hardened retry_with_backoff (+ aws_cli_retry)
#   * write_file_if_changed (atomic, change-detecting)
#   * compose_validate (config --quiet before touching running containers)
#   * wait_for_http (boot-race-resilient local liveness probe)
#   * collect_compose_diagnostics (non-secret failure capture)
#
# BOOT-RACE DISCIPLINE: the VMs boot simultaneously, so a dependency that is not
# yet up is EXPECTED during startup. Retry/wait helpers therefore log interim
# attempts at INFO ("waiting…") and only escalate to ERROR on final exhaustion —
# a peer still booting must never look like a failure in the logs.
#
# SECRET DISCIPLINE: helpers never print the failed command (it may carry
# secret-bearing args), never echo env files, and never dump `docker inspect` or
# the tmpfs secret dir.

# Guard against double-sourcing (aws-cli-retry.sh -> common, and the script also
# sourcing common directly would otherwise re-run trap setup harmlessly, but the
# guard keeps it a no-op and cheap).
if [[ -n "${_FLOWFORM_BOOTSTRAP_COMMON_SOURCED:-}" ]]; then
  return
fi
_FLOWFORM_BOOTSTRAP_COMMON_SOURCED=1

# Name shown in every log line. Each script sets this before sourcing (falls
# back to the sourcing script's basename, then a generic default).
BOOTSTRAP_NAME="${BOOTSTRAP_NAME:-$(basename -- "${0:-bootstrap}" .sh)}"
CURRENT_STEP="initialisation"
DIAGNOSTIC_DIR="${DIAGNOSTIC_DIR:-/var/log/flowform/bootstrap}"

# ---------------------------------------------------------------------------
# Logging + error reporting
# ---------------------------------------------------------------------------
timestamp() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

_log() { # $1 = level ; rest = message
  local level="$1"; shift
  printf '%s | %-5s | %-16s | %s\n' "$(timestamp)" "${level}" "${BOOTSTRAP_NAME}" "$*"
}

info() { _log INFO "$@"; }
warn() { _log WARN "$@" >&2; }

# fatal: single-line hard stop. The ERR trap prints the structured context, so
# fatal only needs to state the reason and exit non-zero.
fatal() { _log ERROR "$@" >&2; exit 1; }

# Backward-compatible aliases so existing call sites (log …, die …) keep working
# unchanged across all three scripts.
log() { info "$@"; }
die() { fatal "$@"; }

begin_step() { CURRENT_STEP="$1"; info "==> ${CURRENT_STEP}"; }
end_step()   { info "    ${CURRENT_STEP}: ok"; }

# ERR trap: reports where a failure happened WITHOUT echoing the command. Wired
# by install_err_trap; the sourcing script calls that once near the top.
on_error() { # $1 exit code  $2 line  $3 function
  local exit_code="$1" line_number="$2" function_name="$3"
  trap - ERR
  _log ERROR "bootstrap failed" >&2
  _log ERROR "  step:     ${CURRENT_STEP}" >&2
  _log ERROR "  function: ${function_name}" >&2
  _log ERROR "  line:     ${line_number}" >&2
  _log ERROR "  exit:     ${exit_code}" >&2
  _log ERROR "  review:   journalctl -u cloud-final -b (or the cloud-init output log)" >&2
  exit "${exit_code}"
}

install_err_trap() {
  # shellcheck disable=SC2154
  trap 'on_error "$?" "$LINENO" "${FUNCNAME[0]:-main}"' ERR
}

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------
require_command() {
  command -v "$1" >/dev/null 2>&1 || fatal "required command is unavailable: $1"
}

check_common_requirements() {
  require_command awk
  require_command grep
  require_command timeout
  require_command flock
}

check_aws_requirements() {
  require_command aws
  require_command jq
}

check_docker_requirements() {
  require_command docker
  docker compose version >/dev/null 2>&1 || fatal "docker compose plugin is unavailable"
}

secret_recovery_guidance() {
  if [[ -n "${BOOTSTRAP_ENDPOINT_URL:-}" ]]; then
    printf '%s' "From the operator workstation run 'infra/deployment/proxmox/scripts/rehearsal sync', then rerun this host bootstrap (or 'rehearsal build')."
  else
    printf '%s' "Verify the secret exists in AWS Secrets Manager for FLOWFORM_SCOPE=${FLOWFORM_SCOPE:-unset}, the instance role can read it, and AWS region/credentials are correct; then rerun bootstrap."
  fi
}

# ---------------------------------------------------------------------------
# Single-instance lock
# ---------------------------------------------------------------------------
# Prevents cloud-init, a systemd unit, and a manual deploy from racing the same
# bootstrap (concurrent env-file swap, docker restart, or DB reset). Uses fd 9.
acquire_lock() { # $1 = lock name (defaults to BOOTSTRAP_NAME)
  local name="${1:-${BOOTSTRAP_NAME}}"
  local lock_dir="${BOOTSTRAP_LOCK_DIR:-/run/lock}"
  local lock_file="${lock_dir}/${name}.lock"
  local attempts="${BOOTSTRAP_LOCK_MAX_ATTEMPTS:-300}"
  local delay="${BOOTSTRAP_LOCK_RETRY_DELAY_SECONDS:-2}"
  local attempt

  [[ "${attempts}" =~ ^[1-9][0-9]*$ ]] || fatal "invalid bootstrap lock attempt count: ${attempts}"
  [[ "${delay}" =~ ^[1-9][0-9]*$ ]] || fatal "invalid bootstrap lock retry delay: ${delay}"
  install -d -m 0755 "$(dirname -- "${lock_file}")"
  exec 9>"${lock_file}"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if flock -n 9; then
      ((attempt > 1)) && info "existing ${name} process finished; acquired lock"
      return 0
    fi
    if ((attempt == 1 || attempt % 10 == 0)); then
      info "waiting for existing ${name} process to finish (attempt ${attempt}/${attempts})"
    fi
    ((attempt == attempts)) && break
    sleep "${delay}"
  done

  fatal "existing ${name} process did not release ${lock_file} after $((attempts * delay)) seconds; inspect its service and cloud-init logs before retrying"
}

# ---------------------------------------------------------------------------
# Timeouts + retries
# ---------------------------------------------------------------------------
run_with_timeout() { # $1 = seconds ; rest = command
  local seconds="$1"; shift
  timeout --foreground --signal=TERM --kill-after=10 "${seconds}" "$@"
}

# retry_with_backoff <description> <attempts> <initial_delay> <per_attempt_timeout> cmd...
#
# Runs cmd until it succeeds or attempts is exhausted. Each attempt is bounded by
# a timeout so a hung dependency cannot block the boot forever. Capped
# exponential backoff (<=30s) with small jitter; NO sleep after the final
# attempt. Interim failures log at INFO ("waiting…", boot-race discipline);
# only exhaustion logs ERROR (with a tail-limited, non-secret diagnostic).
# On success, cmd's captured stdout+stderr is printed so callers can consume it.
retry_with_backoff() {
  local description="$1" attempts="$2" initial_delay="$3" per_attempt_timeout="$4"
  shift 4

  [[ "${attempts}" =~ ^[1-9][0-9]*$ ]]            || fatal "invalid retry attempt count: ${attempts}"
  [[ "${initial_delay}" =~ ^[0-9]+$ ]]            || fatal "invalid retry delay: ${initial_delay}"
  [[ "${per_attempt_timeout}" =~ ^[1-9][0-9]*$ ]] || fatal "invalid per-attempt timeout: ${per_attempt_timeout}"

  local attempt exit_code=0 output="" delay="${initial_delay}"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if output="$(run_with_timeout "${per_attempt_timeout}" "$@" 2>&1)"; then
      [[ -n "${output}" ]] && printf '%s' "${output}"
      return 0
    else
      # Capture the failing status here: a bare `exit_code=$?` after the `if`
      # would read the `if` statement's own status (0 when the condition is
      # false and no branch ran), silently masking the failure and breaking
      # fail-closed behaviour on exhaustion.
      exit_code=$?
    fi

    # Boot-race discipline: interim attempts are "waiting", not errors. Log the
    # first and then every tenth to keep the cloud-init log readable. Progress
    # belongs on stderr: callers capture stdout from successful AWS commands as
    # JSON/parameter data, so mixing a retry log into stdout corrupts that data.
    if ((attempt == 1 || attempt % 10 == 0)); then
      info "waiting for ${description} (attempt ${attempt}/${attempts}, exit ${exit_code})" >&2
    fi

    ((attempt == attempts)) && break

    sleep "$((delay + RANDOM % 3))"
    ((delay < 30)) && delay=$((delay * 2))
    ((delay > 30)) && delay=30
  done

  _log ERROR "${description} failed after ${attempts} attempts (last exit ${exit_code})" >&2
  if [[ -n "${output}" ]]; then
    # Tail-limit and indent; the command itself is never printed.
    printf '%s\n' "${output}" | tail -n 20 | sed 's/^/    /' >&2
  fi
  return "${exit_code}"
}

# aws_cli_retry <description> <aws args...>
#
# Convenience over retry_with_backoff for AWS CLI calls. Prepends the caller's
# AWS_ARGS (region + optional rehearsal --endpoint-url) plus native client
# timeouts and pager suppression. Knobs mirror the previous helper's defaults.
# AWS_ARGS is defined by the sourcing script before this is called.
aws_cli_retry() {
  local description="$1"; shift
  retry_with_backoff "${description}" \
    "${BOOTSTRAP_AWS_MAX_ATTEMPTS:-30}" \
    "${BOOTSTRAP_AWS_RETRY_DELAY_SECONDS:-2}" \
    "${BOOTSTRAP_AWS_ATTEMPT_TIMEOUT_SECONDS:-45}" \
    aws "${AWS_ARGS[@]}" \
    --cli-connect-timeout 10 --cli-read-timeout 30 --no-cli-pager \
    "$@"
}

# ---------------------------------------------------------------------------
# Atomic, change-detecting file write
# ---------------------------------------------------------------------------
# write_file_if_changed <dest> <mode> <content>
#   returns 0 if the file was created/replaced, 1 if content was already identical.
# Lets callers avoid disruptive side effects (e.g. restarting Docker) when
# nothing actually changed.
write_file_if_changed() {
  local destination="$1" mode="$2" content="$3"
  local tmp
  tmp="$(mktemp "${destination}.tmp.XXXXXX")"
  printf '%s\n' "${content}" > "${tmp}"
  chmod "${mode}" "${tmp}"
  if [[ -f "${destination}" ]] && cmp -s "${tmp}" "${destination}"; then
    rm -f "${tmp}"
    return 1
  fi
  mv "${tmp}" "${destination}"
  return 0
}

# ---------------------------------------------------------------------------
# Compose helpers
# ---------------------------------------------------------------------------
# compose_validate <env_file> <compose args...>
# Fails BEFORE any pull/up if interpolation, YAML, a missing variable, or an
# override merge is broken — so a bad config never disturbs running containers.
compose_validate() {
  local env_file="$1"; shift
  docker compose --env-file "${env_file}" "$@" config --quiet \
    || fatal "docker compose configuration validation failed"
}

# collect_compose_diagnostics <env_file> <compose args...>
# Best-effort, NON-SECRET capture after a compose failure. Deliberately excludes
# the env file, `inspect`, and the secret dir. Application/AWS log redaction is
# assumed for the container logs themselves.
collect_compose_diagnostics() {
  local env_file="$1"; shift
  install -d -m 0750 "${DIAGNOSTIC_DIR}"
  local out="${DIAGNOSTIC_DIR}/${BOOTSTRAP_NAME}-failure.log"
  {
    printf 'generated: %s\n\n' "$(timestamp)"
    printf '=== docker status ===\n'
    systemctl status docker --no-pager 2>&1 || true
    printf '\n=== compose services ===\n'
    docker compose --env-file "${env_file}" "$@" ps --all 2>&1 || true
    printf '\n=== recent container logs ===\n'
    docker compose --env-file "${env_file}" "$@" logs --tail 100 --no-color 2>&1 || true
  } > "${out}" 2>&1
  chmod 0640 "${out}"
  warn "compose failed; diagnostics written to ${out}"
}

# ---------------------------------------------------------------------------
# Local liveness probe (boot-race-resilient)
# ---------------------------------------------------------------------------
# wait_for_http <url> <attempts> <delay_seconds> <label>
# Polls a SAME-HOST endpoint. Interim failures log at INFO ("waiting…"); only a
# final timeout is an error. Cross-VM end-to-end checks live in `rehearsal verify`, not
# here — this only confirms the local host's own container is serving.
wait_for_http() {
  local url="$1" attempts="$2" delay="$3" label="$4"
  local attempt
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    # This helper is explicitly for same-host probes. Ignore inherited proxy
    # variables so a private bind address cannot be sent to the egress proxy
    # (which correctly rejects it) instead of the local container.
    if curl --noproxy '*' -fsS --max-time 5 -o /dev/null "${url}"; then
      info "${label} is responding"
      return 0
    fi
    if ((attempt == 1 || attempt % 10 == 0)); then
      info "waiting for ${label} (attempt ${attempt}/${attempts})"
    fi
    ((attempt == attempts)) && break
    sleep "${delay}"
  done
  fatal "${label} did not become healthy at ${url} after ${attempts} attempts"
}

# ---------------------------------------------------------------------------
# SSM path -> env-file (robust JSON parse)
# ---------------------------------------------------------------------------
# render_ssm_path_to_env <json_from_get_parameters_by_path> <out_file>
# Consumes the JSON from `ssm get-parameters-by-path --output json` on stdin,
# derives each env-var name from the parameter's last path segment, validates it
# matches ^[A-Z_][A-Z0-9_]*$, REJECTS multiline values (an env file cannot
# represent them), and appends KEY=value lines to the out file. Avoids the
# tab/newline/whitespace footgun of --output text + IFS parsing.
render_ssm_path_to_env() { # stdin = JSON ; $1 = out file
  local out_file="$1"
  jq -er '
    .Parameters[]
    | (.Name | split("/") | last) as $name
    | select($name | test("^[A-Z_][A-Z0-9_]*$"))
    | if (.Value | test("\n")) then
        error("SSM parameter \($name) has a multiline value, which an env file cannot represent")
      else
        "\($name)=\(.Value)"
      end
  ' >> "${out_file}"
}
