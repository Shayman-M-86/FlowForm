#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
OPERATIONS="${REPO_ROOT}/infra/deployment/aws/operations"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "${TEST_DIR}"' EXIT

mapfile -t scripts < <(find "${OPERATIONS}" -type f -name '*.sh' ! -path '*/_lib/*' | sort)
[[ ${#scripts[@]} -ge 10 ]] || {
  printf 'expected the AWS operation boundaries to be present\n' >&2
  exit 1
}

for script in "${scripts[@]}" "${OPERATIONS}/_lib/common.sh"; do
  bash -n "${script}"
done

for script in "${scripts[@]}"; do
  [[ -x "${script}" ]] || {
    printf 'operation is not executable: %s\n' "${script}" >&2
    exit 1
  }
  "${script}" --help >/dev/null
done

actual="$(
  FLOWFORM_IMAGE_TOOL=/bin/echo \
    "${OPERATIONS}/machine-images/build.sh" app --syntax-only
)"
[[ "${actual}" == "build aws app --syntax-only" ]]

actual="$(
  FLOWFORM_IMAGE_TOOL=/bin/echo \
    "${OPERATIONS}/machine-images/publish.sh" \
      --environment staging --role app --dry-run
)"
[[ "${actual}" == "publish aws --environment staging --role app --dry-run" ]]

mkdir -p "${TEST_DIR}/bin" "${TEST_DIR}/cdk"
cat > "${TEST_DIR}/bin/npx" <<'FAKE_NPX'
#!/usr/bin/env bash
set -Eeuo pipefail
printf '%s\n' "$*" >> "${FLOWFORM_NPX_LOG}"
FAKE_NPX
chmod +x "${TEST_DIR}/bin/npx"

export FLOWFORM_NPX_LOG="${TEST_DIR}/npx.log"
operation_path="${TEST_DIR}/bin:${PATH}"

[[ ! -e "${OPERATIONS}/stacks/deploy-application.sh" ]]

: > "${FLOWFORM_NPX_LOG}"
PATH="${operation_path}" FLOWFORM_CDK_DIR="${TEST_DIR}/cdk" \
  "${OPERATIONS}/stacks/deploy-proxy.sh" \
    --environment staging --skip-diff -- --require-approval never
PATH="${operation_path}" FLOWFORM_CDK_DIR="${TEST_DIR}/cdk" \
  "${OPERATIONS}/stacks/deploy-app.sh" \
    --environment staging --skip-diff -- --require-approval never
cat > "${TEST_DIR}/expected.log" <<'EXPECTED'
cdk deploy -c env=staging --exclusively FlowForm-Staging-Proxy --force --require-approval never
cdk deploy -c env=staging --exclusively FlowForm-Staging-App --force --require-approval never
EXPECTED
cmp "${TEST_DIR}/expected.log" "${FLOWFORM_NPX_LOG}"

: > "${FLOWFORM_NPX_LOG}"
PATH="${operation_path}" FLOWFORM_CDK_DIR="${TEST_DIR}/cdk" \
  "${OPERATIONS}/hosts/replace-role.sh" \
    --environment prod --role app --skip-diff
cat > "${TEST_DIR}/expected.log" <<'EXPECTED'
cdk deploy -c env=prod --exclusively FlowForm-Prod-App --force
EXPECTED
cmp "${TEST_DIR}/expected.log" "${FLOWFORM_NPX_LOG}"

: > "${FLOWFORM_NPX_LOG}"
PATH="${operation_path}" FLOWFORM_CDK_DIR="${TEST_DIR}/cdk" \
  "${OPERATIONS}/hosts/replace-role.sh" \
    --environment prod --role proxy --dry-run
cat > "${TEST_DIR}/expected.log" <<'EXPECTED'
cdk diff -c env=prod --exclusively FlowForm-Prod-Proxy
EXPECTED
cmp "${TEST_DIR}/expected.log" "${FLOWFORM_NPX_LOG}"

set +e
todo_output="$("${OPERATIONS}/configuration/update-role.sh" 2>&1)"
todo_status=$?
set -e
[[ ${todo_status} -eq 3 ]]
[[ "${todo_output}" == TODO:* ]]

printf 'AWS operations boundary checks passed.\n'
