#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="infra/docker/docker-compose.test.yml"
CONTAINER="flowform-backend-test"
PYTEST_ARGS="${*:-tests/}"

# Resolve project root (two levels up from this script's directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../" && pwd)"

cd "${PROJECT_ROOT}"

teardown() {
  echo "==> Tearing down test environment..."
  docker compose -f "${COMPOSE_FILE}" down -v
}
trap teardown EXIT

echo "==> Starting test environment..."
docker compose -f "${COMPOSE_FILE}" up -d --build

echo "==> Waiting for backend-test container to be running..."
WAIT_TIMEOUT=120
WAIT_ELAPSED=0
until [ "$(docker inspect -f '{{.State.Status}}' "${CONTAINER}" 2>/dev/null)" = "running" ]; do
  STATUS="$(docker inspect -f '{{.State.Status}}' "${CONTAINER}" 2>/dev/null)"
  if [ "${STATUS}" = "exited" ] || [ "${STATUS}" = "dead" ]; then
    echo "ERROR: Container '${CONTAINER}' entered terminal state '${STATUS}'."
    echo "==> Container logs:"
    docker logs "${CONTAINER}" 2>&1 || true
    exit 1
  fi
  if [ "${WAIT_ELAPSED}" -ge "${WAIT_TIMEOUT}" ]; then
    echo "ERROR: Timed out after ${WAIT_TIMEOUT}s waiting for container '${CONTAINER}' to start (current state: '${STATUS}')."
    echo "==> Container logs:"
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
