#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

COMPOSE_FILE="${REPO_ROOT}/infra/docker/docker-compose.dev.yml"
CORE_LOAD_SCRIPT="${REPO_ROOT}/scripts/infra/load-core-mock-data.sh"
RESPONSE_LOAD_SCRIPT="${REPO_ROOT}/scripts/infra/load-response-mock-data.sh"
FRONTEND_DIR="${REPO_ROOT}/frontend/my-react-app"

# Change these if your docker compose service names are different.
CORE_DB_SERVICE="${CORE_DB_SERVICE:-postgres-core}"
RESPONSE_DB_SERVICE="${RESPONSE_DB_SERVICE:-postgres-response}"

FRONTEND_LOG="${REPO_ROOT}/frontend/my-react-app/.vite-dev.log"
FRONTEND_PID_FILE="${REPO_ROOT}/frontend/my-react-app/.vite-dev.pid"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

warn() {
  printf '\n[%s] WARNING: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
}

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "Missing file: $path" >&2
    exit 1
  fi
}

require_dir() {
  local path="$1"
  if [[ ! -d "$path" ]]; then
    echo "Missing directory: $path" >&2
    exit 1
  fi
}

wait_for_service() {
  local service="$1"
  local retries="${2:-60}"
  local sleep_seconds="${3:-2}"

  log "Waiting for service '${service}' to become ready..."

  local container_id
  container_id="$(docker compose -f "$COMPOSE_FILE" ps -q "$service")"

  if [[ -z "$container_id" ]]; then
    echo "Could not find container for service: $service" >&2
    exit 1
  fi

  local i
  for ((i=1; i<=retries; i++)); do
    local health_status
    health_status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$container_id" 2>/dev/null || true)"

    if [[ "$health_status" == "healthy" ]]; then
      log "Service '${service}' is healthy."
      return 0
    fi

    if docker compose -f "$COMPOSE_FILE" exec -T "$service" sh -lc \
      'pg_isready -h 127.0.0.1 -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}" >/dev/null 2>&1'
    then
      log "Service '${service}' is accepting connections."
      return 0
    fi

    printf '[%s] Still waiting for %s... (%d/%d)\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$service" "$i" "$retries"
    sleep "$sleep_seconds"
  done

  echo "Timed out waiting for service: $service" >&2
  exit 1
}

run_mock_script() {
  local label="$1"
  local script_path="$2"

  log "Running ${label}..."
  if "$script_path"; then
    log "${label} completed successfully."
    return 0
  fi

  local exit_code=$?
  warn "${label} failed with exit code ${exit_code}. Continuing anyway."
  return "$exit_code"
}

start_frontend() {
  require_dir "$FRONTEND_DIR"

  if [[ -f "$FRONTEND_PID_FILE" ]]; then
    local existing_pid
    existing_pid="$(cat "$FRONTEND_PID_FILE" 2>/dev/null || true)"
    if [[ -n "${existing_pid:-}" ]] && kill -0 "$existing_pid" 2>/dev/null; then
      log "Frontend already running with PID $existing_pid"
      log "Frontend log: $FRONTEND_LOG"
      return 0
    fi
  fi

  log "Starting frontend dev server..."

  (
    cd "$FRONTEND_DIR"

    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    if [[ -s "$NVM_DIR/nvm.sh" ]]; then
      # shellcheck disable=SC1090
      . "$NVM_DIR/nvm.sh"
    fi

    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
  )

  local frontend_pid
  frontend_pid="$(cat "$FRONTEND_PID_FILE")"

  log "Frontend started with PID $frontend_pid"
  log "Frontend log: $FRONTEND_LOG"
}

main() {
  require_file "$COMPOSE_FILE"
  require_file "$CORE_LOAD_SCRIPT"
  require_file "$RESPONSE_LOAD_SCRIPT"

  chmod +x "$CORE_LOAD_SCRIPT" "$RESPONSE_LOAD_SCRIPT"

  log "Starting docker compose stack..."
  docker compose -f "$COMPOSE_FILE" up -d

  wait_for_service "$CORE_DB_SERVICE"
  wait_for_service "$RESPONSE_DB_SERVICE"

  local core_mock_failed=0
  local response_mock_failed=0

  if ! run_mock_script "core mock data load" "$CORE_LOAD_SCRIPT"; then
    core_mock_failed=1
  fi

  if ! run_mock_script "response mock data load" "$RESPONSE_LOAD_SCRIPT"; then
    response_mock_failed=1
  fi

  start_frontend

  if (( core_mock_failed || response_mock_failed )); then
    warn "Frontend was started, but one or more mock data scripts failed."
    exit 1
  fi

  log "Done."
}

main "$@"
