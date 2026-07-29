#!/usr/bin/env bash
# TODO(migration): Update paths, contracts, and runtime wiring for infra-new before this file is used.
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT="${REPO_ROOT}/infra/deployment/aws/scripts/seed-observability-secret.sh"
TEST_DIR="$(mktemp -d)"
MOCK_BIN="${TEST_DIR}/bin"
AWS_LOG="${TEST_DIR}/aws.log"
TOKEN_FILE="${TEST_DIR}/grafana-token"

cleanup() {
  rm -rf -- "${TEST_DIR}"
}

trap cleanup EXIT
mkdir -p "${MOCK_BIN}"
printf '%s' 'super-secret-test-token' >"${TOKEN_FILE}"

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
"${SCRIPT}" --apply | grep -Fq 'Added a new secret version'
[[ "$(wc -l <"${AWS_LOG}")" -eq 3 ]]
! grep -Fq 'super-secret-test-token' "${AWS_LOG}"

printf 'PASS: observability secret seeding keeps the token out of AWS CLI arguments\n'
