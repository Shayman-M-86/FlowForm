#!/usr/bin/env bash
set -Eeuo pipefail

# FlowForm rehearsal database host bootstrap. VM 240 has no default route and
# its PostgreSQL image is preloaded by Packer. The only boot-time egress is a
# temporary nftables rule permitting the host AWS CLI to reach Squid while it
# retrieves the two managed application-role passwords.

# Shared library provides log/die (as info/fatal aliases), the ERR trap, the
# flock guard, timeouts, the hardened retry helpers, and diagnostics.
# BOOTSTRAP_NAME tags every log line. NOTE: this script is PROXMOX-ONLY — prod
# uses RDS — so it may make rehearsal-specific assumptions the app/proxy scripts
# must not.
BOOTSTRAP_NAME="bootstrap-db"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# Pull in the shared library before any log/die call. The db-secret EXIT trap is
# installed below (close_bootstrap_egress) and coexists with common's ERR trap.
# shellcheck source=bootstrap-common.sh
source "${SCRIPT_DIR}/bootstrap-common.sh"
install_err_trap

: "${FLOWFORM_SCOPE:?set FLOWFORM_SCOPE}"
: "${PROXY_PRIVATE_IP:?set PROXY_PRIVATE_IP}"
: "${DB_PRIVATE_IP:?set DB_PRIVATE_IP}"
: "${AWS_REGION:?set AWS_REGION}"

COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/infra/containers/strategies/rehearsal/compose/db.yml}"
SECRET_DIR="${FLOWFORM_SECRET_DIR:-/run/flowform/secrets}"
BOOTSTRAP_CHAIN="bootstrap_egress"
EGRESS_OPEN=0

# AWS_ARGS is consumed by aws_cli_retry (from the common library sourced above).
AWS_ARGS=(--region "${AWS_REGION}")
if [[ -n "${BOOTSTRAP_ENDPOINT_URL:-}" ]]; then
  AWS_ARGS+=(--endpoint-url "${BOOTSTRAP_ENDPOINT_URL}")
fi

export HTTP_PROXY="http://${PROXY_PRIVATE_IP}:3128"
export HTTPS_PROXY="${HTTP_PROXY}"
export NO_PROXY="localhost,127.0.0.1,169.254.169.254"
export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" no_proxy="${NO_PROXY}"

close_bootstrap_egress() {
  if (( EGRESS_OPEN == 1 )); then
    nft flush chain inet flowform_db "${BOOTSTRAP_CHAIN}" >/dev/null 2>&1 || true
    EGRESS_OPEN=0
    log "closed temporary bootstrap egress"
  fi
}
trap close_bootstrap_egress EXIT INT TERM HUP

open_bootstrap_egress() {
  nft list chain inet flowform_db "${BOOTSTRAP_CHAIN}" >/dev/null 2>&1 \
    || die "nftables bootstrap chain is not loaded"
  nft flush chain inet flowform_db "${BOOTSTRAP_CHAIN}"
  # Mark open before adding the rule so the EXIT trap still flushes the chain
  # if nft fails or the process is interrupted between these operations.
  EGRESS_OPEN=1
  nft add rule inet flowform_db "${BOOTSTRAP_CHAIN}" \
    ip daddr "${PROXY_PRIVATE_IP}" tcp dport 3128 accept
  log "opened temporary egress to ${PROXY_PRIVATE_IP}:3128"
}

fetch_secret_string() {
  local secret_id="flowform/${FLOWFORM_SCOPE}/db-secrets" output
  output="$(aws_cli_retry "Secrets Manager database secret" \
    secretsmanager get-secret-value \
    --secret-id "${secret_id}" \
    --query SecretString --output text)" \
    || die "could not read required secret ${secret_id}. $(secret_recovery_guidance)"
  [[ -n "${output}" && "${output}" != None ]] \
    || die "required secret ${secret_id} returned an empty SecretString. $(secret_recovery_guidance)"
  printf '%s' "${output}"
}

# Extract one key from a secret JSON object WITHOUT placing the secret on argv:
# the blob is fed on stdin (via write_secret_key's builtin-printf pipe) and only
# the key name is an argument. jq is provisioned into every image by
# install-base.sh (python3 is not on minimal AL2023). Fails on a missing/empty
# value so a bad secret fails the boot rather than writing an empty file.
extract_key() { # $1 = json key ; JSON object on stdin
  jq -je --arg k "$1" '.[$k] // "" | select(length > 0)' \
    || die "database secret JSON is missing or has an empty value for key: $1. $(secret_recovery_guidance)"
}

# Feed a JSON blob to extract_key via a builtin printf pipe (printf is a bash
# builtin: no fork, no argv exposure, no here-string temp file).
write_secret_key() { # $1 = json blob  $2 = json key  $3 = out file
  printf '%s' "$1" | extract_key "$2" > "$3"
}

materialise_secrets() {
  install -d -m 0700 "${SECRET_DIR}"
  if ! findmnt -t tmpfs --target "${SECRET_DIR}" >/dev/null 2>&1; then
    mount -t tmpfs -o size=8m,mode=0700 tmpfs "${SECRET_DIR}"
  fi
  chmod 0700 "${SECRET_DIR}"

  local db_json
  db_json="$(fetch_secret_string)"

  umask 177
  # This password belongs to the current ephemeral cluster, not to a single
  # bootstrap invocation. Preserve it across idempotent convergence runs on the
  # same boot; replacing it while retaining PostgreSQL would make later admin
  # verification use a password the live role never received.
  if [[ ! -s "${SECRET_DIR}/DATABASE_INIT_PASSWORD.secret.txt" ]]; then
    openssl rand -hex 24 >"${SECRET_DIR}/DATABASE_INIT_PASSWORD.secret.txt"
  fi
  write_secret_key "${db_json}" db_core_app_password \
    "${SECRET_DIR}/DATABASE_CORE_APP_PASSWORD.secret.txt"
  write_secret_key "${db_json}" db_response_app_password \
    "${SECRET_DIR}/DATABASE_RESPONSE_APP_PASSWORD.secret.txt"
  # Compose implements local file-backed secrets as bind mounts and therefore
  # preserves the source ownership/mode. The official postgres:17 entrypoint
  # drops to postgres (uid/gid 999) before running initdb scripts, so grant only
  # that runtime identity read access while the files remain inside root-owned
  # tmpfs on the host.
  chown 999:999 "${SECRET_DIR}"/*.secret.txt
  chmod 0400 "${SECRET_DIR}"/*.secret.txt
  umask 022
  log "materialised ephemeral init and managed app-role secrets"
}

assert_egress_closed() {
  # Structural check: the bootstrap chain must contain ZERO rule objects. Parsing
  # nft's JSON (nft -j) and counting rule entries is robust against formatting
  # changes and cannot be fooled by a rule whose rendered text does not match a
  # brittle grep pattern. Any remaining rule fails the boot.
  local rules
  rules="$(nft -j list chain inet flowform_db "${BOOTSTRAP_CHAIN}")" \
    || die "could not verify the bootstrap egress chain"
  printf '%s' "${rules}" \
    | jq -e '[.nftables[] | select(has("rule"))] | length == 0' >/dev/null \
    || die "temporary bootstrap egress rules remain installed"
}

# The PostgreSQL app roles are created (with these passwords) by the init scripts,
# which the postgres entrypoint runs ONLY against an empty data dir. The data dir
# is tmpfs (see rehearsal compose), so a fresh VM boot always reinitialises with
# the current passwords — correct by construction. The gap is a DEPLOY RE-RUN on a
# still-running VM after the managed passwords ROTATED: the live cluster keeps the
# old roles, so the backend authenticates with new passwords the DB never learned.
#
# We close that gap with a fingerprint of the two managed app-role passwords (NOT
# the per-run random init password). When it changes against the recorded value
# and a cluster already exists, we tear the cluster down (-v drops the data
# volume) so the entrypoint reinitialises the roles from the new passwords. When
# it is unchanged we leave the running cluster untouched — no needless reset.
#
# The fingerprint is a SHA-256 of the password FILES (values never touch argv) and
# is itself non-secret; it lives on the persistent FS, not the tmpfs secret dir.
DB_SECRET_FINGERPRINT_FILE="${DB_SECRET_FINGERPRINT_FILE:-/var/lib/flowform/db-secret.fingerprint}"

current_secret_fingerprint() {
  # Hash the two managed password files by PATH; sha256sum never sees the values
  # on argv. Sorted, fixed order → stable across runs for identical passwords.
  sha256sum \
    "${SECRET_DIR}/DATABASE_CORE_APP_PASSWORD.secret.txt" \
    "${SECRET_DIR}/DATABASE_RESPONSE_APP_PASSWORD.secret.txt" \
    | awk '{ print $1 }' | sha256sum | awk '{ print $1 }'
}

cluster_volume_exists() {
  # The rehearsal db compose names its project "flowform-db". Count ALL
  # containers (--all), not just running ones: a STOPPED-but-present container
  # still holds a cluster whose roles would be stale after a password change, and
  # skipping the reset there would leave the DB with the old passwords. Any
  # tracked container — running or stopped — means a reset is required.
  docker compose -f "${COMPOSE_FILE}" ps --all --quiet 2>/dev/null | grep -q .
}

reset_cluster_if_secret_changed() {
  local current recorded
  current="$(current_secret_fingerprint)"
  recorded=""
  [[ -f "${DB_SECRET_FINGERPRINT_FILE}" ]] && recorded="$(cat "${DB_SECRET_FINGERPRINT_FILE}")"

  if [[ -n "${recorded}" && "${recorded}" != "${current}" ]] && cluster_volume_exists; then
    # LOUD, unmistakable banner: this is the ONE destructive action in the whole
    # bootstrap. The rehearsal data dir is tmpfs, so `down -v` discards the entire
    # cluster (all data) to force the postgres entrypoint to reinitialise the app
    # roles from the rotated passwords. There is no in-place ALTER ROLE path here
    # (that would be a Layer-3 DB-lifecycle change). Make it obvious in the log
    # exactly what is being destroyed and why.
    warn "############################################################"
    warn "# DESTRUCTIVE: managed DB passwords changed since last deploy"
    warn "# tearing down cluster 'flowform-db' with 'docker compose down -v'"
    warn "# ALL rehearsal database data will be discarded and the cluster"
    warn "# reinitialised so the app roles pick up the rotated passwords."
    warn "############################################################"
    FLOWFORM_SECRET_DIR="${SECRET_DIR}" docker compose -f "${COMPOSE_FILE}" down -v \
      || die "could not tear down the existing cluster for password reinitialisation"
  elif [[ -z "${recorded}" ]]; then
    log "no prior DB-secret fingerprint — treating as first initialisation"
  else
    log "managed DB passwords unchanged — leaving any existing cluster in place"
  fi
}

record_secret_fingerprint() {
  install -d -m 0755 "$(dirname "${DB_SECRET_FINGERPRINT_FILE}")"
  current_secret_fingerprint > "${DB_SECRET_FINGERPRINT_FILE}"
  chmod 0644 "${DB_SECRET_FINGERPRINT_FILE}"
}

# Verify one application role can actually authenticate and run a trivial query.
# Runs psql INSIDE the postgres container (the host has no psql on minimal
# AL2023). The password is passed as a container ENV var via `exec -e`, read from
# the tmpfs secret file — it never appears on the host or container argv. Boot-
# race-resilient: retried, INFO while waiting, ERROR only on final timeout.
verify_database_role() { # $1 db  $2 user  $3 password-file  $4 label
  local db="$1" user="$2" password_file="$3" label="$4"
  # Read the password into an EXPORTED shell var and pass it through with the
  # bare `--env PGPASSWORD` form (NAME, no value). Docker copies the value from
  # THIS process's environment into the container — the secret never appears on
  # any argv (host or container) or in the process table, unlike `--env NAME=val`.
  # -w disables any password prompt; -q keeps psql quiet.
  local PGPASSWORD rc=0
  PGPASSWORD="$(cat "${password_file}")"
  export PGPASSWORD
  # `|| rc=$?` keeps set -e / the ERR trap from firing before we can clean up the
  # exported secret; we surface the failure explicitly below.
  retry_with_backoff "${label} role login" \
    "${BOOTSTRAP_DB_VERIFY_ATTEMPTS:-30}" "${BOOTSTRAP_DB_VERIFY_DELAY_SECONDS:-2}" \
    "${BOOTSTRAP_DB_VERIFY_TIMEOUT_SECONDS:-15}" \
    docker compose -f "${COMPOSE_FILE}" exec -T \
    --env PGPASSWORD postgres \
    psql -h 127.0.0.1 -U "${user}" -d "${db}" -w -q -c 'SELECT 1;' >/dev/null \
    || rc=$?
  unset PGPASSWORD
  ((rc == 0)) || die "${label} role (${user}) could not authenticate to ${db}"
  info "${label} role (${user}) authenticated to ${db}"
}

verify_database_roles() {
  verify_database_role flowform_core     flowform_core_app \
    "${SECRET_DIR}/DATABASE_CORE_APP_PASSWORD.secret.txt"     "core"
  verify_database_role flowform_response flowform_response_app \
    "${SECRET_DIR}/DATABASE_RESPONSE_APP_PASSWORD.secret.txt" "response"
}

start_database() {
  [[ -f "${COMPOSE_FILE}" ]] || die "compose file not found: ${COMPOSE_FILE}"
  reset_cluster_if_secret_changed
  local health_timeout="${BOOTSTRAP_HEALTH_TIMEOUT_SECONDS:-180}"
  if ! FLOWFORM_SECRET_DIR="${SECRET_DIR}" docker compose -f "${COMPOSE_FILE}" \
      up -d --pull never --wait --wait-timeout "${health_timeout}"; then
    collect_compose_diagnostics "/dev/null" -f "${COMPOSE_FILE}"
    die "database compose stack did not become healthy within ${health_timeout}s"
  fi
  # Confirm BOTH managed app roles can actually log in before recording success.
  verify_database_roles
  # Only record AFTER a healthy start AND verified logins, so a failed reinit is
  # retried next run rather than being masked by a stale fingerprint.
  record_secret_fingerprint
  log "database compose stack is healthy and both app roles authenticate"
}

main() {
  log "scope=${FLOWFORM_SCOPE} db=${DB_PRIVATE_IP} proxy=${PROXY_PRIVATE_IP}"

  begin_step "Validating configuration"
  check_common_requirements
  check_aws_requirements
  check_docker_requirements
  require_command nft
  acquire_lock "${BOOTSTRAP_NAME}"
  end_step

  begin_step "Fetching managed DB secrets"
  open_bootstrap_egress
  materialise_secrets
  close_bootstrap_egress
  assert_egress_closed
  end_step

  begin_step "Starting database cluster"
  start_database
  end_step

  info "bootstrap completed successfully"
}

main "$@"
