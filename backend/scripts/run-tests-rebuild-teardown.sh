#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# Run Tests (Full Rebuild + Teardown)
#
# Builds all services, runs tests in the backend container, then fully tears
# everything down containers + volumes. Clean environment every run.
#
# Usage:
#   ./run-tests-rebuild-teardown.sh [--ai] [--verbose] [--logs=all|none] [--log-tail=N] [pytest args]
#
# Options:
#   --ai              Compact output for agents/CI: hide Compose startup chatter
#                     and omit pytest captured stdout/log sections.
#   --verbose, -v     Show full Docker/test command output and run pytest without
#                     the script's quiet defaults.
#   --logs=all        On failure, print Docker logs from all services.
#   --logs=none       On failure, skip Docker logs. This is the default.
#   --log-tail=N      Number of Docker log lines to print with --logs=all
#                     (default: 250).
#   --help, -h        Print this help text.
#
# Any other arguments are passed through to pytest. If no pytest args are
# supplied, the script runs tests/.
#
# Examples:
#   ./run-tests-rebuild-teardown.sh
#   ./run-tests-rebuild-teardown.sh --ai -k public_link
#   ./run-tests-rebuild-teardown.sh --verbose
#   ./run-tests-rebuild-teardown.sh --logs=all
#   ./run-tests-rebuild-teardown.sh --logs=none tests/integration
#   ./run-tests-rebuild-teardown.sh tests/ -k public_link
# ------------------------------------------------------------------------------

COMPOSE_FILE="infra/docker/docker-compose.test.yml"
CONTAINER="flowform-backend-test"

LOG_MODE="none"
LOG_TAIL="250"
VERBOSE=0
AI_MODE=0

PYTEST_ARGS=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --verbose|-v)
      VERBOSE=1
      shift
      ;;
    --ai)
      AI_MODE=1
      shift
      ;;
    --logs=all)
      LOG_MODE="all"
      shift
      ;;
    --logs=none)
      LOG_MODE="none"
      shift
      ;;
    --log-tail=*)
      LOG_TAIL="${1#*=}"
      shift
      ;;
    --help|-h)
      sed -n '4,34p' "$0"
      exit 0
      ;;
    *)
      PYTEST_ARGS+=("$1")
      shift
      ;;
  esac
done

if [ "${#PYTEST_ARGS[@]}" -eq 0 ]; then
  PYTEST_ARGS=("tests/")
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../" && pwd)"

cd "${PROJECT_ROOT}"

COLOR_RESET="\033[0m"
COLOR_BLUE="\033[34m"
COLOR_GREEN="\033[32m"
COLOR_RED="\033[31m"

STEP_LOG="/tmp/flowform-script-step.log"

_failed=0

compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

print_section() {
  echo
  echo "==> $1"
}

supports_spinner() {
  [ -t 1 ] && [ "${VERBOSE}" -eq 0 ]
}

run_with_spinner() {
  local message="$1"
  shift

  local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
  local pid
  local i=0
  local exit_code
  local status_column_width=62

  rm -f "${STEP_LOG}"

  "$@" >"${STEP_LOG}" 2>&1 &
  pid=$!

  if supports_spinner; then
    printf "\n\n\n\n"
    while kill -0 "${pid}" 2>/dev/null; do
      i=$(((i + 1) % ${#spin}))
      printf "\033[2A\r\033[2K==> ${COLOR_BLUE}%s${COLOR_RESET} %-*s waiting\n\n" "${spin:$i:1}" "${status_column_width}" "${message}"
      sleep 0.1
    done
  else
    echo "==> ${message}"
  fi

  wait "${pid}"
  exit_code=$?

  if supports_spinner; then
    if [ "${exit_code}" -eq 0 ]; then
      printf "\033[2A\r\033[2K==> ${COLOR_GREEN}✓${COLOR_RESET} %-*s ${COLOR_GREEN}Done${COLOR_RESET}\n" "${status_column_width}" "${message}"
    else
      printf "\033[2A\r\033[2K==> ${COLOR_RED}✗${COLOR_RESET} %-*s ${COLOR_RED}failed${COLOR_RESET}\n" "${status_column_width}" "${message}"
    fi
  fi

  if [ "${exit_code}" -ne 0 ]; then
    echo
    echo "ERROR: ${message} failed."
    tail -n 80 "${STEP_LOG}" || true
  fi

  return "${exit_code}"
}

dump_logs() {
  case "${LOG_MODE}" in
    all)
      print_section "Docker logs from all services, last ${LOG_TAIL} lines"
      compose logs --no-color --tail="${LOG_TAIL}" 2>&1 || true
      ;;
    none)
      return 0
      ;;
    *)
      echo "ERROR: Invalid log mode '${LOG_MODE}'. Use all or none."
      ;;
  esac
}

wait_for_backend() {
  local wait_timeout=120
  local wait_elapsed=0
  local status

  until [ "$(docker inspect -f '{{.State.Status}}' "${CONTAINER}" 2>/dev/null || true)" = "running" ]; do
    status="$(docker inspect -f '{{.State.Status}}' "${CONTAINER}" 2>/dev/null || true)"

    if [ "${status}" = "exited" ] || [ "${status}" = "dead" ]; then
      echo "ERROR: Container '${CONTAINER}' entered terminal state '${status}'."
      return 1
    fi

    if [ "${wait_elapsed}" -ge "${wait_timeout}" ]; then
      echo "ERROR: Timed out after ${wait_timeout}s waiting for '${CONTAINER}'."
      echo "Current state: '${status:-unknown}'"
      return 1
    fi

    sleep 1
    wait_elapsed=$((wait_elapsed + 1))
  done
}

teardown() {
  if [ "${_failed}" -eq 1 ]; then
    print_section "Tests failed"
    dump_logs
  fi

  if [ "${VERBOSE}" -eq 1 ]; then
    print_section "Cleaning up test environment"
    compose down -v --remove-orphans
  else
    run_with_spinner "Cleaning up test environment" compose down -v --remove-orphans || true
  fi
}

trap teardown EXIT

if [ "${VERBOSE}" -eq 1 ]; then
  print_section "Starting test environment"
  compose up -d --build
else
  run_with_spinner "Building test images" compose build || {
    _failed=1
    exit 1
  }

  if [ "${AI_MODE}" -eq 1 ]; then
    run_with_spinner "Starting test environment" compose up -d --no-build --quiet-pull || {
      _failed=1
      exit 1
    }
  else
    print_section "Starting test environment"
    compose up -d --no-build --quiet-pull || {
      _failed=1
      exit 1
    }
  fi
fi

if [ "${VERBOSE}" -eq 1 ]; then
  print_section "Waiting for backend-test container"
  wait_for_backend
  echo "Backend container is running."
else
  run_with_spinner "Waiting for backend-test container" wait_for_backend || {
    _failed=1
    exit 1
  }
fi

print_section "Running tests"

if [ "${VERBOSE}" -eq 1 ]; then
  PYTEST_OUTPUT_MODE=()
else
  PYTEST_OUTPUT_MODE=("-q" "--tb=short")

  if [ "${AI_MODE}" -eq 1 ]; then
    PYTEST_OUTPUT_MODE+=("--show-capture=no" "--color=no")
  fi
fi

echo "uv run pytest ${PYTEST_OUTPUT_MODE[*]} ${PYTEST_ARGS[*]}"

set +e

if [ -t 0 ] && [ -t 1 ]; then
  docker exec -it "${CONTAINER}" uv run pytest "${PYTEST_OUTPUT_MODE[@]}" "${PYTEST_ARGS[@]}"
else
  docker exec "${CONTAINER}" uv run pytest "${PYTEST_OUTPUT_MODE[@]}" "${PYTEST_ARGS[@]}"
fi

TEST_EXIT_CODE=$?
set -e

if [ "${TEST_EXIT_CODE}" -ne 0 ]; then
  _failed=1
  exit "${TEST_EXIT_CODE}"
fi

print_section "Tests passed"
