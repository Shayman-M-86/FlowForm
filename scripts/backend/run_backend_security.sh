#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"

install_uv_if_missing() {
  if command -v uv >/dev/null 2>&1; then
    echo "==> uv already installed: $(uv --version)"
    return
  fi

  echo "==> uv not found. Installing..."

  export UV_UNMANAGED_INSTALL="${HOME}/.local/bin"
  mkdir -p "${UV_UNMANAGED_INSTALL}"

  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | sh
  else
    echo "Error: neither curl nor wget is available, so uv cannot be installed." >&2
    exit 1
  fi

  export PATH="${UV_UNMANAGED_INSTALL}:${PATH}"

  if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv installation completed, but uv is still not on PATH." >&2
    exit 1
  fi

  echo "==> Installed uv: $(uv --version)"
}

cleanup() {
  echo "==> Uninstalling tools..."
  uv tool uninstall pip-audit bandit || true
}

trap cleanup EXIT

install_uv_if_missing

cd "${BACKEND_DIR}"

echo "==> Generating requirements.txt..."
uv pip compile pyproject.toml --extra dev --extra test -o requirements.txt

echo "==> Installing tools..."
uv tool install pip-audit@latest
uv tool install bandit@latest

pip_audit_status=0
bandit_app_status=0
bandit_tests_status=0

echo "==> Running pip-audit..."
set +e
uvx pip-audit -r requirements.txt
pip_audit_status=$?
set -e

echo "==> Running Bandit on app..."
set +e
uvx bandit -r app -lll -iii
bandit_app_status=$?
set -e

echo "==> Running Bandit on tests..."
# Ignore common test-only noise:
#   B101: use of assert
#   B110: try/except/pass
# Only report High severity + High confidence issues.
set +e
uvx bandit -r tests -lll -iii -s B101,B110
bandit_tests_status=$?
set -e

echo
echo "==> Scan summary"

if [ "${pip_audit_status}" -ne 0 ]; then
  echo " - pip-audit found dependency vulnerabilities."
fi

if [ "${bandit_app_status}" -ne 0 ]; then
  echo " - Bandit found High severity / High confidence issues in app."
fi

if [ "${bandit_tests_status}" -ne 0 ]; then
  echo " - Bandit found High severity / High confidence issues in tests."
fi

if [ "${pip_audit_status}" -ne 0 ] || [ "${bandit_app_status}" -ne 0 ] || [ "${bandit_tests_status}" -ne 0 ]; then
  echo
  echo "==> Failing because one or more security scans reported issues."
  exit 1
fi

echo
echo "==> All security scans passed."