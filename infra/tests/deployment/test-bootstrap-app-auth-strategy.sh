#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
BOOTSTRAP="${REPO_ROOT}/infra/deployment/bootstrap/bootstrap-app.sh"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "${TEST_DIR}"' EXIT

write_backend_env() {
  local core_mode="$1" response_mode="$2"
  {
    printf 'DATABASE_CORE_AUTH_MODE=%s\n' "${core_mode}"
    printf 'DATABASE_RESPONSE_AUTH_MODE=%s\n' "${response_mode}"
  } > "${TEST_DIR}/backend.env"
}

run_valid_case() {
  local target="$1" core_mode="$2" response_mode="$3" expected="$4" output
  write_backend_env "${core_mode}" "${response_mode}"
  output="$(
    export FLOWFORM_DEPLOYMENT_TARGET="${target}"
    export FLOWFORM_SCOPE=nonprod
    export PROXY_PRIVATE_IP=10.10.10.10
    export APP_PRIVATE_IP=10.10.10.20
    export AWS_REGION=ap-southeast-2
    export BOOTSTRAP_BACKEND_ENV="${TEST_DIR}/backend.env"
    export BOOTSTRAP_DRY_RUN=0
    # shellcheck source=../../deployment/bootstrap/bootstrap-app.sh
    source "${BOOTSTRAP}"
    validate_database_auth_strategy
    [[ "${DATABASE_AUTH_STRATEGY}" == "${expected}" ]]
    DRY_RUN=1
    materialise_secrets
  )"
  printf '%s' "${output}"
}

run_invalid_case() {
  local target="$1" core_mode="$2" response_mode="$3"
  write_backend_env "${core_mode}" "${response_mode}"
  if (
    export FLOWFORM_DEPLOYMENT_TARGET="${target}"
    export FLOWFORM_SCOPE=nonprod
    export PROXY_PRIVATE_IP=10.10.10.10
    export APP_PRIVATE_IP=10.10.10.20
    export AWS_REGION=ap-southeast-2
    export BOOTSTRAP_BACKEND_ENV="${TEST_DIR}/backend.env"
    export BOOTSTRAP_DRY_RUN=0
    # shellcheck source=../../deployment/bootstrap/bootstrap-app.sh
    source "${BOOTSTRAP}"
    validate_database_auth_strategy
  ) >/dev/null 2>&1; then
    printf 'strategy unexpectedly accepted target=%s core=%s response=%s\n' \
      "${target}" "${core_mode}" "${response_mode}" >&2
    exit 1
  fi
}

aws_output="$(run_valid_case aws iam iam iam)"
grep -F 'write 2 common secret files' <<<"${aws_output}" >/dev/null
if grep -F 'DATABASE_CORE_APP_PASSWORD, DATABASE_RESPONSE_APP_PASSWORD' <<<"${aws_output}" >/dev/null; then
  printf 'AWS IAM dry run still plans to materialise database passwords\n' >&2
  exit 1
fi

rehearsal_output="$(run_valid_case rehearsal password password password)"
grep -F 'write 4 secret files' <<<"${rehearsal_output}" >/dev/null
grep -F 'DATABASE_CORE_APP_PASSWORD, DATABASE_RESPONSE_APP_PASSWORD' <<<"${rehearsal_output}" >/dev/null

run_invalid_case aws password password
run_invalid_case rehearsal iam iam
run_invalid_case aws iam password

cat > "${TEST_DIR}/images.env" <<'EOF'
BACKEND_IMAGE=908123139858.dkr.ecr.ap-southeast-2.amazonaws.com/flowform-staging-backend@sha256:1111111111111111111111111111111111111111111111111111111111111111
ALLOY_IMAGE=908123139858.dkr.ecr.ap-southeast-2.amazonaws.com/flowform-staging-alloy@sha256:2222222222222222222222222222222222222222222222222222222222222222
EOF
ecr_dry_run="$(
  export FLOWFORM_DEPLOYMENT_TARGET=aws
  export FLOWFORM_SCOPE=nonprod
  export PROXY_PRIVATE_IP=10.10.10.10
  export APP_PRIVATE_IP=10.10.10.20
  export AWS_REGION=ap-southeast-2
  export BOOTSTRAP_DRY_RUN=1
  source "${BOOTSTRAP}"
  login_ecr_for_images "${TEST_DIR}/images.env" BACKEND_IMAGE ALLOY_IMAGE
)"
grep -F 'would authenticate Docker to 1 private ECR registry' <<<"${ecr_dry_run}" >/dev/null

(
  # shellcheck source=../../deployment/bootstrap/bootstrap-common.sh
  source "${REPO_ROOT}/infra/deployment/bootstrap/bootstrap-common.sh"
  wait_call=""
  retry_with_backoff() {
    wait_call="$*"
  }
  wait_for_tcp "Squid readiness" 10.10.10.10 3128 7 3 2
  [[ "${wait_call}" == "Squid readiness 7 3 2 bash -c exec 3<>\"/dev/tcp/\$1/\$2\" _ 10.10.10.10 3128" ]]
)

run_materialise_case() {
  local target="$1" core_mode="$2" response_mode="$3" case_dir
  case_dir="${TEST_DIR}/materialise-${target}"
  mkdir -p "${case_dir}/secrets"
  : > "${case_dir}/fetches"
  touch \
    "${case_dir}/secrets/DATABASE_CORE_APP_PASSWORD.secret.txt" \
    "${case_dir}/secrets/DATABASE_RESPONSE_APP_PASSWORD.secret.txt"
  write_backend_env "${core_mode}" "${response_mode}"

  (
    export FLOWFORM_DEPLOYMENT_TARGET="${target}"
    export FLOWFORM_SCOPE=nonprod
    export PROXY_PRIVATE_IP=10.10.10.10
    export APP_PRIVATE_IP=10.10.10.20
    export AWS_REGION=ap-southeast-2
    export BOOTSTRAP_BACKEND_ENV="${TEST_DIR}/backend.env"
    export BOOTSTRAP_DRY_RUN=0
    export FLOWFORM_SECRET_DIR="${case_dir}/secrets"
    # shellcheck source=../../deployment/bootstrap/bootstrap-app.sh
    source "${BOOTSTRAP}"
    findmnt() { return 0; }
    fetch_secret_string() {
      printf '%s\n' "$1" >> "${case_dir}/fetches"
      case "$1" in
        app-secrets)
          printf '%s' '{"app_secret_key":"app","auth0_mgmt_secret":"auth0"}'
          ;;
        db-secrets)
          printf '%s' '{"db_core_app_password":"core","db_response_app_password":"response"}'
          ;;
      esac
    }
    validate_database_auth_strategy
    materialise_secrets
  ) >/dev/null
}

run_materialise_case aws iam iam
[[ "$(cat "${TEST_DIR}/materialise-aws/fetches")" == "app-secrets" ]]
[[ -f "${TEST_DIR}/materialise-aws/secrets/FLOWFORM_APP_SECRET_KEY.secret.txt" ]]
[[ -f "${TEST_DIR}/materialise-aws/secrets/FLOWFORM_AUTH0_MGMT_SECRET.secret.txt" ]]
[[ ! -e "${TEST_DIR}/materialise-aws/secrets/DATABASE_CORE_APP_PASSWORD.secret.txt" ]]
[[ ! -e "${TEST_DIR}/materialise-aws/secrets/DATABASE_RESPONSE_APP_PASSWORD.secret.txt" ]]

run_materialise_case rehearsal password password
[[ "$(sort "${TEST_DIR}/materialise-rehearsal/fetches")" == $'app-secrets\ndb-secrets' ]]
[[ -f "${TEST_DIR}/materialise-rehearsal/secrets/DATABASE_CORE_APP_PASSWORD.secret.txt" ]]
[[ -f "${TEST_DIR}/materialise-rehearsal/secrets/DATABASE_RESPONSE_APP_PASSWORD.secret.txt" ]]

printf '[test-bootstrap-app-auth-strategy] PASS\n'
