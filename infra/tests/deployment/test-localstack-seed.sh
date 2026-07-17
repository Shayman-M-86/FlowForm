#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
CONTRACT="${REPO_ROOT}/infra/deployment/config/runtime-parameter-contract.json"
SEED_SCRIPT="${REPO_ROOT}/infra/containers/rehearsal/services/localstack/seed-localstack.sh"
TLS_COMPOSE="${REPO_ROOT}/infra/containers/rehearsal/compose/compose.tls-shim.yml"
PROXY_OVERRIDE="${REPO_ROOT}/infra/containers/rehearsal/compose/compose.proxy.rehearsal.yml"
APP_CLOUD_INIT="${REPO_ROOT}/infra/deployment/proxmox/terraform/cloud-init/app.user-data.yaml.template"
PROXMOX_VARIABLES="${REPO_ROOT}/infra/deployment/proxmox/terraform/variables.tf"
PROXY_CLOUD_INIT="${REPO_ROOT}/infra/deployment/proxmox/terraform/cloud-init/proxy.user-data.yaml.template"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "${TEST_DIR}"' EXIT

mkdir -p "${TEST_DIR}/bin"
export AWS_CALL_LOG="${TEST_DIR}/aws-calls.log"

cat > "${TEST_DIR}/bin/curl" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

cat > "${TEST_DIR}/bin/aws" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
printf '%q ' "$@" >> "${AWS_CALL_LOG}"
printf '\n' >> "${AWS_CALL_LOG}"

while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --endpoint-url|--region) shift 2 ;;
    *) shift ;;
  esac
done
service="$1"
action="$2"
shift 2

case "${service}:${action}" in
  secretsmanager:describe-secret)
    if [[ " $* " == *" --query ARN "* ]]; then
      printf 'arn:aws:secretsmanager:ap-southeast-2:000000000000:secret:flowform/nonprod/linkage-secret\n'
      exit 0
    fi
    exit 1
    ;;
  secretsmanager:create-secret) printf 'created\n' ;;
  secretsmanager:put-secret-value) printf 'updated\n' ;;
  kms:describe-key)
    if [[ " $* " == *" alias/"* ]]; then
      exit 1
    fi
    printf 'arn:aws:kms:ap-southeast-2:000000000000:key/rehearsal-key\n'
    ;;
  kms:create-key) printf 'rehearsal-key\n' ;;
  kms:create-alias) ;;
  ssm:put-parameter) printf '1\n' ;;
  *) printf 'unexpected mock AWS call: %s %s %s\n' "${service}" "${action}" "$*" >&2; exit 2 ;;
esac
EOF

chmod +x "${TEST_DIR}/bin/aws" "${TEST_DIR}/bin/curl"
export PATH="${TEST_DIR}/bin:${PATH}"
export RUNTIME_PARAMETER_CONTRACT="${CONTRACT}"
export AWS_ENDPOINT_URL="http://10.10.10.30:4566"

while IFS= read -r key; do
  export "${key}=test-${key,,}"
done < <(jq -r '.runtime_groups[].parameters[].seed_value_key // empty' "${CONTRACT}" | sort -u)
export AWS_REGION="ap-southeast-2"

"${SEED_SCRIPT}" >/dev/null

expected_parameters="$((
  $(jq '[.runtime_groups[].parameters[]] | length' "${CONTRACT}") + 3
))"
actual_parameters="$(grep -c 'ssm put-parameter' "${AWS_CALL_LOG}")"
[[ "${actual_parameters}" == "${expected_parameters}" ]] \
  || { printf 'expected %s SSM writes, found %s\n' "${expected_parameters}" "${actual_parameters}" >&2; exit 1; }

while IFS= read -r expected_name; do
  grep -F -- "--name ${expected_name} " "${AWS_CALL_LOG}" >/dev/null \
    || { printf 'missing seeded parameter: %s\n' "${expected_name}" >&2; exit 1; }
done < <(jq -r '
  .runtime_groups[] as $group
  | $group.parameters[].name
  | "/flowform/nonprod/\($group.path)/\(.)"
' "${CONTRACT}")

grep -F 'https://ssm.localstack.test/_localstack/health' "${TLS_COMPOSE}" >/dev/null
for hostname in secretsmanager.localstack.test ssm.localstack.test kms.localstack.test; do
  grep -F "${hostname}:10.10.10.30" "${PROXY_OVERRIDE}" >/dev/null
done
for cloud_init in "${APP_CLOUD_INIT}" "${PROXY_CLOUD_INIT}"; do
  grep -F '/etc/pki/ca-trust/source/anchors/flowform-rehearsal-ca.crt' "${cloud_init}" >/dev/null
  grep -F 'AWS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt' "${cloud_init}" >/dev/null
  grep -F 'BOOTSTRAP_AWS_MAX_ATTEMPTS=120' "${cloud_init}" >/dev/null
done
grep -F 'COMPOSE_OVERRIDE_FILE=/opt/flowform/repo/infra/containers/rehearsal/compose/compose.app.rehearsal.yml' "${APP_CLOUD_INIT}" >/dev/null
grep -F 'COMPOSE_FORCE_RECREATE=1' "${APP_CLOUD_INIT}" >/dev/null
grep -E 'FLOWFORM_EMAIL_FROM_ADDRESS += "no-reply@flow-form.com.au"' "${PROXMOX_VARIABLES}" >/dev/null
grep -E 'FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP += "false"' "${PROXMOX_VARIABLES}" >/dev/null

printf '[test-localstack-seed] PASS\n'
