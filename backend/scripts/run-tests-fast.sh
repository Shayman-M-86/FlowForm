#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# Run Tests (Fast Run, No Rebuild)
#
# Starts the backend container (and required services if not already running),
# runs tests, then stops the backend container while keeping databases and
# volumes intact.
#
# Usage:
#   ./run-tests.sh [pytest args]
# ------------------------------------------------------------------------------

COMPOSE_FILE="infra/docker/docker-compose.test.yml"
BACKEND_SERVICE="backend-test"
CONTAINER="flowform-backend-test"
PYTEST_ARGS="${*:-tests/}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../" && pwd)"

cd "${PROJECT_ROOT}"

shutdown() {
  echo "==> Stopping backend container (keeping databases)..."
  docker compose -f "${COMPOSE_FILE}" stop "${BACKEND_SERVICE}" || true
}
trap shutdown EXIT

echo "==> Starting test environment..."
docker compose -f "${COMPOSE_FILE}" up -d "${BACKEND_SERVICE}"

echo "==> Waiting for backend-test container to be running..."
WAIT_TIMEOUT=120
WAIT_ELAPSED=0

until [ "$(docker inspect -f '{{.State.Status}}' "${CONTAINER}" 2>/dev/null)" = "running" ]; do
  STATUS="$(docker inspect -f '{{.State.Status}}' "${CONTAINER}" 2>/dev/null)"

  if [ "${STATUS}" = "exited" ] || [ "${STATUS}" = "dead" ]; then
    echo "ERROR: Container '${CONTAINER}' entered terminal state '${STATUS}'."
    docker logs "${CONTAINER}" 2>&1 || true
    exit 1
  fi

  if [ "${WAIT_ELAPSED}" -ge "${WAIT_TIMEOUT}" ]; then
    echo "ERROR: Timed out waiting for container '${CONTAINER}'."
    docker logs "${CONTAINER}" 2>&1 || true
    exit 1
  fi

  sleep 1
  WAIT_ELAPSED=$((WAIT_ELAPSED + 1))
done

echo "==> Running tests: uv run pytest ${PYTEST_ARGS}"
if [ -t 0 ] && [ -t 1 ]; then
  docker exec -it "${CONTAINER}" uv run pytest ${PYTEST_ARGS}
else
  docker exec "${CONTAINER}" uv run pytest ${PYTEST_ARGS}
fi