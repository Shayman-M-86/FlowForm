#!/usr/bin/env bash
set -Eeuo pipefail

# Bring up the local dev stack from a clean slate.
#
#   1. Generate the machine-local Postgres passwords (no-op if they exist).
#   2. Fetch the real dev secrets from Secrets Manager into the tmpfs dir.
#   3. Recreate the compose stack with a fresh backend image build.
#
# By default the Postgres volumes are DELETED so the containers re-run
# infra/database/init and recreate the application roles. This is the
# recovery path for a volume left half-initialised by a failed first start:
# once a data directory exists, Postgres skips /docker-entrypoint-initdb.d
# forever, so roles like flowform_core_app are never created and the backend
# fails with "password authentication failed".
#
# Usage:
#   scripts/dev/start-dev-stack.sh              # prompts before wiping volumes
#   scripts/dev/start-dev-stack.sh --yes        # no prompt (for automation)
#   scripts/dev/start-dev-stack.sh --keep-data  # preserve volumes
#
# Mock data is not loaded here — run scripts/dev/load-core-mock-data.sh and
# scripts/dev/load-response-mock-data.sh afterwards, or use
# scripts/dev/bootstrap-dev-and-load-mocks.sh.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

COMPOSE_FILE="${REPO_ROOT}/infra/containers/strategies/dev/compose/compose.yml"
GENERATE_SCRIPT="${REPO_ROOT}/scripts/secrets/generate-secrets.sh"
FETCH_SCRIPT="${REPO_ROOT}/scripts/secrets/fetch-dev-secrets.sh"

KEEP_DATA=0
ASSUME_YES=0

log()  { printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die()  { printf '\nerror: %s\n' "$*" >&2; exit 1; }

usage() {
  sed -n '3,25p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'
}

while (( $# )); do
  case "$1" in
    --keep-data) KEEP_DATA=1 ;;
    --yes|-y)    ASSUME_YES=1 ;;
    -h|--help)   usage; exit 0 ;;
    *)           die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

[[ -f "$COMPOSE_FILE"    ]] || die "missing compose file: $COMPOSE_FILE"
[[ -f "$GENERATE_SCRIPT" ]] || die "missing script: $GENERATE_SCRIPT"
[[ -f "$FETCH_SCRIPT"    ]] || die "missing script: $FETCH_SCRIPT"

command -v docker >/dev/null 2>&1 || die "docker not found"
docker info >/dev/null 2>&1 || die "docker daemon is not reachable"

# fetch-dev-secrets.sh enforces this too, but failing here keeps us from
# prompting about destroying volumes before discovering we cannot proceed.
[[ -n "${XDG_RUNTIME_DIR:-}" ]] \
  || die "XDG_RUNTIME_DIR is not set; secrets must land on tmpfs, not disk."

SECRET_DIR="${FLOWFORM_SECRET_DIR:-${XDG_RUNTIME_DIR}/flowform-secrets}"

# ---------------------------------------------------------------------------
# Confirm the destructive step up front, before any work is done.
# ---------------------------------------------------------------------------
if (( ! KEEP_DATA && ! ASSUME_YES )); then
  if [[ -t 0 ]]; then
    printf '\nThis deletes the dev Postgres volumes; all local dev data\n'
    printf 'and any loaded mock data will be lost. Use --keep-data to skip.\n'
    read -r -p 'Continue? [y/N] ' reply
    [[ "$reply" =~ ^[Yy]$ ]] || die "aborted"
  else
    die "refusing to delete volumes without a TTY; pass --yes or --keep-data"
  fi
fi

# ---------------------------------------------------------------------------
# 1 + 2. Secrets. generate-secrets.sh never overwrites an existing file, so
# the persisted DB passwords stay in sync with the volumes they initialise.
# ---------------------------------------------------------------------------
log "Generating machine-local dev secrets (existing files are kept)..."
bash "$GENERATE_SCRIPT" dev

log "Fetching dev secrets from AWS Secrets Manager..."
if ! FLOWFORM_SECRET_DIR="$SECRET_DIR" bash "$FETCH_SCRIPT"; then
  die "secret fetch failed — is your 'aws login --profile ${AWS_PROFILE:-flowform-dev}' session current?"
fi

export FLOWFORM_SECRET_DIR="$SECRET_DIR"

# ---------------------------------------------------------------------------
# 3. Recreate the stack.
# ---------------------------------------------------------------------------
if (( KEEP_DATA )); then
  log "Stopping stack (volumes preserved)..."
  docker compose -f "$COMPOSE_FILE" down
else
  log "Stopping stack and deleting Postgres volumes..."
  docker compose -f "$COMPOSE_FILE" down -v
fi

log "Building and starting the stack..."
docker compose -f "$COMPOSE_FILE" up -d --build

log "Stack is up. FLOWFORM_SECRET_DIR=${FLOWFORM_SECRET_DIR}"
printf '\nExport this in your shell rc so plain "docker compose" works too:\n'
printf '  export FLOWFORM_SECRET_DIR="$XDG_RUNTIME_DIR/flowform-secrets"\n\n'
printf 'Follow startup with:\n'
printf '  docker compose -f %s logs -f backend\n\n' "$COMPOSE_FILE"
