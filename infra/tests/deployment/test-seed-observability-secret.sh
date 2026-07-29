#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT="${REPO_ROOT}/infra/deployment/aws/scripts/seed-observability-secret.sh"
TEST_DIR="$(mktemp -d)"
MOCK_BIN="${TEST_DIR}/bin"
AWS_LOG="${TEST_DIR}/aws.log"
TOKEN_FILE="${TEST_DIR}/grafana-token"
DOTENV_FILE="${TEST_DIR}/grafana.env"
INVALID_FILE="${TEST_DIR}/invalid.env"

cleanup() {
  rm -rf -- "${TEST_DIR}"
}

trap cleanup EXIT
mkdir -p "${MOCK_BIN}"
printf '%s' 'super-secret-test-token' >"${TOKEN_FILE}"
printf '%s\n' 'GRAFANA_CLOUD_TOKEN="super-secret-test-token"' >"${DOTENV_FILE}"
printf '%s\n' 'ANOTHER_TOKEN="super-secret-test-token"' >"${INVALID_FILE}"

cat >"${MOCK_BIN}/aws" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

printf '%q ' "$@" >>"${AWS_LOG}"
printf '\n' >>"${AWS_LOG}"

case "$1 $2" in
  "sts get-caller-identity")
    printf '%s\n' '908123139858'
    ;;
  "secretsmanager describe-secret")
    ;;
  "secretsmanager put-secret-value")
    secret_file=""
    while [[ $# -gt 0 ]]; do
      if [[ "$1" == "--secret-string" ]]; then
        secret_file="${2#file://}"
        break
      fi
      shift
    done
    [[ -f "${secret_file}" ]]
    grep -Fq '"grafana_cloud_token": "super-secret-test-token"' "${secret_file}"
    printf '%s\n' 'test-version'
    ;;
esac
EOF
chmod +x "${MOCK_BIN}/aws"

export AWS_LOG
export PATH="${MOCK_BIN}:${PATH}"
export GRAFANA_CLOUD_TOKEN_FILE="${TOKEN_FILE}"

"${SCRIPT}" | grep -Fq 'DRY RUN'
[[ "$(wc -l <"${AWS_LOG}")" -eq 2 ]]
! grep -Fq 'super-secret-test-token' "${AWS_LOG}"

: >"${AWS_LOG}"
GRAFANA_CLOUD_TOKEN_FILE="${DOTENV_FILE}" \
  "${SCRIPT}" --apply | grep -Fq 'Added a new secret version'
[[ "$(wc -l <"${AWS_LOG}")" -eq 3 ]]
! grep -Fq 'super-secret-test-token' "${AWS_LOG}"

if GRAFANA_CLOUD_TOKEN_FILE="${INVALID_FILE}" "${SCRIPT}" >/dev/null 2>&1; then
  printf 'ERROR: unexpected dotenv variable was accepted\n' >&2
  exit 1
fi

printf 'PASS: observability secret seeding accepts token and dotenv files without leaking the token\n'
