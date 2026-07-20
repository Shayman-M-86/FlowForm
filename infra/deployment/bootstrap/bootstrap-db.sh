#!/usr/bin/env bash
set -Eeuo pipefail

# FlowForm rehearsal database host bootstrap. VM 240 has no default route and
# its PostgreSQL image is preloaded by Packer. The only boot-time egress is a
# temporary nftables rule permitting the host AWS CLI to reach Squid while it
# retrieves the two managed application-role passwords.

log() { printf '[bootstrap-db %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die() { printf '[bootstrap-db %s] ERROR: %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; exit 1; }

: "${FLOWFORM_SCOPE:?set FLOWFORM_SCOPE}"
: "${PROXY_PRIVATE_IP:?set PROXY_PRIVATE_IP}"
: "${DB_PRIVATE_IP:?set DB_PRIVATE_IP}"
: "${AWS_REGION:?set AWS_REGION}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/infra/containers/strategies/rehearsal/compose/db.yml}"
SECRET_DIR="${FLOWFORM_SECRET_DIR:-/run/flowform/secrets}"
BOOTSTRAP_CHAIN="bootstrap_egress"
EGRESS_OPEN=0

AWS_ARGS=(--region "${AWS_REGION}")
if [[ -n "${BOOTSTRAP_ENDPOINT_URL:-}" ]]; then
  AWS_ARGS+=(--endpoint-url "${BOOTSTRAP_ENDPOINT_URL}")
fi

# shellcheck source=aws-cli-retry.sh
source "${SCRIPT_DIR}/aws-cli-retry.sh"

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
  aws_cli_retry "Secrets Manager database secret" \
    secretsmanager get-secret-value \
    --secret-id "flowform/${FLOWFORM_SCOPE}/db-secrets" \
    --query SecretString --output text
}

extract_key() {
  python3 -c '
import json, sys
value = json.loads(sys.argv[1]).get(sys.argv[2], "")
if not value:
    raise SystemExit(f"error: empty/missing key {sys.argv[2]!r}")
sys.stdout.write(value)
' "$1" "$2"
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
  openssl rand -hex 24 >"${SECRET_DIR}/DATABASE_INIT_PASSWORD.secret.txt"
  extract_key "${db_json}" db_core_app_password \
    >"${SECRET_DIR}/DATABASE_CORE_APP_PASSWORD.secret.txt"
  extract_key "${db_json}" db_response_app_password \
    >"${SECRET_DIR}/DATABASE_RESPONSE_APP_PASSWORD.secret.txt"
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
  local rules
  rules="$(nft list chain inet flowform_db "${BOOTSTRAP_CHAIN}")" \
    || die "could not verify the bootstrap egress chain"
  if grep -Eq ' tcp dport 3128 .* accept' <<<"${rules}"; then
    die "temporary bootstrap egress rule remains installed"
  fi
}

start_database() {
  [[ -f "${COMPOSE_FILE}" ]] || die "compose file not found: ${COMPOSE_FILE}"
  FLOWFORM_SECRET_DIR="${SECRET_DIR}" docker compose -f "${COMPOSE_FILE}" \
    up -d --pull never --wait --wait-timeout 180
  log "database compose stack is healthy"
}

main() {
  log "scope=${FLOWFORM_SCOPE} db=${DB_PRIVATE_IP} proxy=${PROXY_PRIVATE_IP}"
  open_bootstrap_egress
  materialise_secrets
  close_bootstrap_egress
  assert_egress_closed
  start_database
  log "done"
}

main "$@"
