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
grep -Fx 'build aws app --syntax-only' <<< "${actual}" >/dev/null

actual="$(
  FLOWFORM_IMAGE_TOOL=/bin/echo \
    "${OPERATIONS}/machine-images/publish.sh" \
      --environment staging --role app --dry-run
)"
grep -Fx 'publish aws --environment staging --role app --dry-run' \
  <<< "${actual}" >/dev/null

mkdir -p "${TEST_DIR}/bin" "${TEST_DIR}/cdk"
cat > "${TEST_DIR}/bin/npx" <<'FAKE_NPX'
#!/usr/bin/env bash
set -Eeuo pipefail
printf '%s\n' "$*" >> "${FLOWFORM_NPX_LOG}"
printf 'fake npx output: %s\n' "$*"

if [[ "${1:-}" == "cdk" && "${2:-}" == "deploy" ]]; then
  while (( $# > 0 )); do
    if [[ "$1" == "--outputs-file" ]]; then
      printf '{"FlowForm-Test":{"Output":"value"}}\n' > "$2"
      break
    fi
    shift
  done
  if [[ "${FLOWFORM_FAKE_NPX_FAIL_DEPLOY:-0}" == "1" ]]; then
    printf 'simulated CDK deployment failure\n' >&2
    exit 17
  fi
fi
FAKE_NPX
cat > "${TEST_DIR}/bin/aws" <<'FAKE_AWS'
#!/usr/bin/env bash
set -Eeuo pipefail
printf '%s\n' "$*" >> "${FLOWFORM_AWS_LOG}"
printf -- '----------------------------------\n'
printf '|       DescribeStackEvents      |\n'
printf '|  simulated CREATE_FAILED event |\n'
printf -- '----------------------------------\n'
FAKE_AWS
chmod +x "${TEST_DIR}/bin/npx" "${TEST_DIR}/bin/aws"

export FLOWFORM_NPX_LOG="${TEST_DIR}/npx.log"
export FLOWFORM_AWS_LOG="${TEST_DIR}/aws.log"
operation_path="${TEST_DIR}/bin:${PATH}"
artifact_root="${TEST_DIR}/operation-artifacts"
operation_id="test-stack-operations"
github_output="${TEST_DIR}/github-output"
github_step_summary="${TEST_DIR}/github-step-summary"
: > "${github_output}"
: > "${github_step_summary}"

[[ ! -e "${OPERATIONS}/stacks/deploy-application.sh" ]]

: > "${FLOWFORM_NPX_LOG}"
PATH="${operation_path}" \
  FLOWFORM_CDK_DIR="${TEST_DIR}/cdk" \
  FLOWFORM_OPERATION_ARTIFACT_ROOT="${artifact_root}" \
  FLOWFORM_OPERATION_ID="${operation_id}" \
  "${OPERATIONS}/stacks/deploy-proxy.sh" \
    --environment staging --skip-diff -- --require-approval never
PATH="${operation_path}" \
  FLOWFORM_CDK_DIR="${TEST_DIR}/cdk" \
  FLOWFORM_OPERATION_ARTIFACT_ROOT="${artifact_root}" \
  FLOWFORM_OPERATION_ID="${operation_id}" \
  GITHUB_OUTPUT="${github_output}" \
  GITHUB_STEP_SUMMARY="${github_step_summary}" \
  "${OPERATIONS}/stacks/deploy-app.sh" \
    --environment staging --skip-diff -- --require-approval never
cat > "${TEST_DIR}/expected.log" <<EXPECTED
cdk deploy -c env=staging --exclusively FlowForm-Staging-Proxy --force --require-approval never --outputs-file ${artifact_root}/${operation_id}/cdk-deploy-FlowForm-Staging-Proxy/stack-outputs.json
cdk deploy -c env=staging --exclusively FlowForm-Staging-App --force --require-approval never --outputs-file ${artifact_root}/${operation_id}/cdk-deploy-FlowForm-Staging-App/stack-outputs.json
EXPECTED
cmp "${TEST_DIR}/expected.log" "${FLOWFORM_NPX_LOG}"

: > "${FLOWFORM_NPX_LOG}"
PATH="${operation_path}" \
  FLOWFORM_CDK_DIR="${TEST_DIR}/cdk" \
  FLOWFORM_OPERATION_ARTIFACT_ROOT="${artifact_root}" \
  FLOWFORM_OPERATION_ID="${operation_id}" \
  "${OPERATIONS}/hosts/replace-role.sh" \
    --environment prod --role app --skip-diff
cat > "${TEST_DIR}/expected.log" <<EXPECTED
cdk deploy -c env=prod --exclusively FlowForm-Prod-App --force --outputs-file ${artifact_root}/${operation_id}/cdk-deploy-FlowForm-Prod-App/stack-outputs.json
EXPECTED
cmp "${TEST_DIR}/expected.log" "${FLOWFORM_NPX_LOG}"

: > "${FLOWFORM_NPX_LOG}"
PATH="${operation_path}" \
  FLOWFORM_CDK_DIR="${TEST_DIR}/cdk" \
  FLOWFORM_OPERATION_ARTIFACT_ROOT="${artifact_root}" \
  FLOWFORM_OPERATION_ID="${operation_id}" \
  "${OPERATIONS}/hosts/replace-role.sh" \
    --environment prod --role proxy --dry-run
cat > "${TEST_DIR}/expected.log" <<'EXPECTED'
cdk diff -c env=prod --exclusively FlowForm-Prod-Proxy
EXPECTED
cmp "${TEST_DIR}/expected.log" "${FLOWFORM_NPX_LOG}"

app_artifacts="${artifact_root}/${operation_id}/cdk-deploy-FlowForm-Staging-App"
[[ -s "${app_artifacts}/cdk-deploy.log" ]]
[[ -s "${app_artifacts}/stack-outputs.json" ]]
[[ -s "${app_artifacts}/operation.jsonl" ]]
[[ -s "${app_artifacts}/summary.json" ]]
grep -F '"operation_id": "test-stack-operations"' "${app_artifacts}/summary.json" >/dev/null
grep -F '"source_commit": "' "${app_artifacts}/summary.json" >/dev/null
grep -F '"outcome": "success"' "${app_artifacts}/summary.json" >/dev/null
grep -F '"exit_code": 0' "${app_artifacts}/summary.json" >/dev/null
grep -F '"stack": "FlowForm-Staging-App"' "${app_artifacts}/summary.json" >/dev/null
[[ "$(stat -c '%a' "${app_artifacts}/summary.json")" == "600" ]]
[[ "$(stat -c '%a' "${app_artifacts}/cdk-deploy.log")" == "600" ]]
grep -Fx "flowform_operation_id=${operation_id}" "${github_output}" >/dev/null
grep -Fx "flowform_operation_artifact_dir=${app_artifacts}" "${github_output}" >/dev/null
grep -F '### FlowForm operation: `cdk-deploy-FlowForm-Staging-App`' \
  "${github_step_summary}" >/dev/null

failure_operation_id="failed-stack-operation"
: > "${FLOWFORM_NPX_LOG}"
: > "${FLOWFORM_AWS_LOG}"
set +e
PATH="${operation_path}" \
  FLOWFORM_CDK_DIR="${TEST_DIR}/cdk" \
  FLOWFORM_OPERATION_ARTIFACT_ROOT="${artifact_root}" \
  FLOWFORM_OPERATION_ID="${failure_operation_id}" \
  FLOWFORM_FAKE_NPX_FAIL_DEPLOY=1 \
  "${OPERATIONS}/stacks/deploy-app.sh" \
    --environment staging --skip-diff -- --require-approval never
failure_status=$?
set -e
[[ ${failure_status} -eq 17 ]]

failure_artifacts="${artifact_root}/${failure_operation_id}/cdk-deploy-FlowForm-Staging-App"
[[ -s "${failure_artifacts}/cdk-deploy.log" ]]
[[ -s "${failure_artifacts}/cloudformation-events.log" ]]
[[ -s "${failure_artifacts}/summary.json" ]]
grep -F 'cloudformation describe-stack-events --stack-name FlowForm-Staging-App' \
  "${FLOWFORM_AWS_LOG}" >/dev/null
grep -F '"outcome": "failure"' "${failure_artifacts}/summary.json" >/dev/null
grep -F '"exit_code": 17' "${failure_artifacts}/summary.json" >/dev/null
grep -F '"failure_events": "'"${failure_artifacts}"'/cloudformation-events.log"' \
  "${failure_artifacts}/summary.json" >/dev/null

interrupt_operation_id="interrupted-operation"
set +e
FLOWFORM_OPERATION_ARTIFACT_ROOT="${artifact_root}" \
  FLOWFORM_OPERATION_ID="${interrupt_operation_id}" \
  bash -c '
    set -Eeuo pipefail
    source "$1"
    operation_init "interrupt-test" shared
    operation_set_summary_metadata phase "waiting"
    operation_install_exit_trap
    kill -TERM "$$"
  ' _ "${OPERATIONS}/_lib/common.sh"
interrupt_status=$?
set -e
[[ ${interrupt_status} -eq 143 ]]
interrupt_summary="${artifact_root}/${interrupt_operation_id}/interrupt-test/summary.json"
[[ -s "${interrupt_summary}" ]]
grep -F '"outcome": "failure"' "${interrupt_summary}" >/dev/null
grep -F '"exit_code": 143' "${interrupt_summary}" >/dev/null
grep -F '"phase": "waiting"' "${interrupt_summary}" >/dev/null

set +e
todo_output="$("${OPERATIONS}/configuration/update-role.sh" 2>&1)"
todo_status=$?
set -e
[[ ${todo_status} -eq 3 ]]
[[ "${todo_output}" == TODO:* ]]

printf 'AWS operations boundary checks passed.\n'
