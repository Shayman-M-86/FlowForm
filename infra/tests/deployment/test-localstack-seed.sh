#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
CONTRACT="${REPO_ROOT}/infra/deployment/config/runtime-parameter-contract.json"
SEED_SCRIPT="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/localstack/seed-localstack.sh"
SYNC_SCRIPT="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/localstack/sync-secrets-into-localstack.sh"
TLS_COMPOSE="${REPO_ROOT}/infra/containers/strategies/rehearsal/fixtures/compose.tls-shim.yml"
PROXY_OVERRIDE="${REPO_ROOT}/infra/containers/strategies/rehearsal/compose/proxy.override.yml"
APP_CLOUD_INIT="${REPO_ROOT}/infra/deployment/proxmox/cloud-init/templates/app.yaml.tftpl"
PROXMOX_VARIABLES="${REPO_ROOT}/infra/deployment/proxmox/terraform/variables.tf"
PROXY_CLOUD_INIT="${REPO_ROOT}/infra/deployment/proxmox/cloud-init/templates/proxy.yaml.tftpl"
LOCALSTACK_CLOUD_INIT="${REPO_ROOT}/infra/deployment/proxmox/cloud-init/templates/localstack.yaml.tftpl"
DB_CLOUD_INIT="${REPO_ROOT}/infra/deployment/proxmox/cloud-init/templates/db.yaml.tftpl"
DB_COMPOSE="${REPO_ROOT}/infra/containers/strategies/rehearsal/compose/db.yml"
DB_BOOTSTRAP="${REPO_ROOT}/infra/deployment/bootstrap/bootstrap-db.sh"
APP_BOOTSTRAP="${REPO_ROOT}/infra/deployment/bootstrap/bootstrap-app.sh"
BUILD_COMMAND="${REPO_ROOT}/infra/deployment/proxmox/scripts/lib/cmd_build.sh"
VERIFY_COMMAND="${REPO_ROOT}/infra/deployment/proxmox/scripts/lib/cmd_verify.sh"
TLS_SHIM_CADDYFILE="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/tls-shim/Caddyfile"
REGISTRY_COMPOSE="${REPO_ROOT}/infra/containers/strategies/rehearsal/fixtures/compose.registry.yml"
LOCALSTACK_COMPOSE="${REPO_ROOT}/infra/containers/strategies/rehearsal/fixtures/compose.localstack.yml"
REHEARSAL_ALLOWED_DOMAINS="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/squid/allowed-domains.txt"
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
export AWS_ENDPOINT_URL="http://127.0.0.1:4566"

# Export every non-secret seed value validated by seed-localstack.sh.
while IFS= read -r key; do
  export "${key}=test-${key,,}"
done < <(jq -r '(.runtime_groups[].parameters[].seed_value_key // empty),
                (.secret_seed_value_keys[]? // empty)' "${CONTRACT}" | sort -u)
export FLOWFORM_CORS_ORIGINS='["https://studio.example.test"]'
export FLOWFORM_CORS_SUPPORTS_CREDENTIALS=true
export AWS_REGION="ap-southeast-2"

"${SEED_SCRIPT}" >/dev/null

# Non-secret env-backed runtime values + computed backend KMS ARN + two
# scope-level values (KMS ARN and region). Linkage ARN arrives during sync.
expected_parameters="$(($(jq '[.runtime_groups[].parameters[] | select(.seed_value_key != null)] | length' "${CONTRACT}") + 3))"
actual_parameters="$(grep -c 'ssm put-parameter' "${AWS_CALL_LOG}")"
[[ "${actual_parameters}" == "${expected_parameters}" ]] \
  || { printf 'expected %s SSM writes, found %s\n' "${expected_parameters}" "${actual_parameters}" >&2; exit 1; }

while IFS= read -r expected_name; do
  grep -F -- "--name ${expected_name} " "${AWS_CALL_LOG}" >/dev/null \
    || { printf 'missing seeded parameter: %s\n' "${expected_name}" >&2; exit 1; }
done < <(jq -r '
  .runtime_groups[] as $group
  | $group.parameters[]
  | select(.seed_value_key != null or .name == "FLOWFORM_ENCRYPTION_KMS_KEY_ARN")
  | .name
  | "/flowform/nonprod/\($group.path)/\(.)"
' "${CONTRACT}")

# Boot seeding is secret-free. Managed secrets arrive later via `rehearsal sync`.
if grep -F 'secretsmanager ' "${AWS_CALL_LOG}" >/dev/null; then
  printf 'boot seed unexpectedly called Secrets Manager\n' >&2; exit 1
fi

# Deploy-time synchronization must own LocalStack readiness too, so callers
# cannot race a reachable VM whose container is still health: starting.
grep -F 'wait_for_localstack' "${SYNC_SCRIPT}" >/dev/null
grep -F 'curl -fsS --max-time 5 "${LS_ENDPOINT}/_localstack/health"' "${SYNC_SCRIPT}" >/dev/null

grep -F 'https://ssm.localstack.test/_localstack/health' "${TLS_COMPOSE}" >/dev/null
for hostname in secretsmanager.localstack.test ssm.localstack.test kms.localstack.test; do
  grep -F "${hostname}:10.10.10.30" "${PROXY_OVERRIDE}" >/dev/null
done
for cloud_init in "${APP_CLOUD_INIT}" "${PROXY_CLOUD_INIT}" "${DB_CLOUD_INIT}"; do
  grep -F '/etc/pki/ca-trust/source/anchors/flowform-rehearsal-ca.crt' "${cloud_init}" >/dev/null
  grep -F 'AWS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt' "${cloud_init}" >/dev/null
  grep -F 'BOOTSTRAP_AWS_MAX_ATTEMPTS=120' "${cloud_init}" >/dev/null
done
grep -F 'COMPOSE_FORCE_RECREATE=1' "${APP_CLOUD_INIT}" >/dev/null
# Cross-host traces require the isolated app clock to use the synchronized proxy.
grep -F 'bindaddress 10.10.10.10' "${PROXY_CLOUD_INIT}" >/dev/null
grep -F 'bindaddress ::1' "${PROXY_CLOUD_INIT}" >/dev/null
grep -F 'allow 10.10.10.0/24' "${PROXY_CLOUD_INIT}" >/dev/null
grep -F 'server 10.10.10.10 iburst prefer minpoll 4 maxpoll 4' "${APP_CLOUD_INIT}" >/dev/null
grep -F 'Disabled: the rehearsal app has no route to public NTP.' "${APP_CLOUD_INIT}" >/dev/null
grep -F 'ExecStartPre=' "${APP_CLOUD_INIT}" >/dev/null
grep -F 'ln -sfn /usr/share/chrony/ntp-pool.sources' "${PROXY_CLOUD_INIT}" >/dev/null
grep -F 'rm -f /run/chrony.d/ntp-pool.sources' "${APP_CLOUD_INIT}" >/dev/null
grep -F 'chronyc -n waitsync 30 0.0 0.0 1' "${APP_CLOUD_INIT}" >/dev/null
grep -F 'chronyc -a makestep' "${APP_CLOUD_INIT}" >/dev/null
grep -F 'chronyc -n waitsync 10 0.05 0.0 1' "${APP_CLOUD_INIT}" >/dev/null
grep -F 'proxy clock synchronized and serving private NTP' "${VERIFY_COMMAND}" >/dev/null
grep -F 'app clock synchronized from proxy private NTP' "${VERIFY_COMMAND}" >/dev/null
# Cloud-init prepares and enables reboot recovery, while `rehearsal build` owns
# first convergence. Starting these services here would recreate the old lock
# race and make app cloud-init wait for images the orchestrator has not built.
for service in app proxy db; do
  cloud_init="${REPO_ROOT}/infra/deployment/proxmox/cloud-init/templates/${service}.yaml.tftpl"
  grep -F "systemctl, enable, flowform-${service}.service" "${cloud_init}" >/dev/null
  if grep -F "systemctl, enable, --now, flowform-${service}.service" "${cloud_init}" >/dev/null; then
    printf 'cloud-init starts flowform-%s.service during first convergence\n' "${service}" >&2; exit 1
  fi
done
if grep -F -- '- [ /opt/flowform/scripts/run-bootstrap-app.sh ]' "${APP_CLOUD_INIT}" >/dev/null \
  || grep -F -- '- [ /opt/flowform/scripts/run-bootstrap-proxy.sh ]' "${PROXY_CLOUD_INIT}" >/dev/null; then
  printf 'cloud-init directly invokes app/proxy convergence\n' >&2; exit 1
fi
grep -F 'BOOTSTRAP_PREPARE_ONLY' "${APP_BOOTSTRAP}" >/dev/null
grep -F 'PUBLISH_PREPARE_ONLY=1' "${BUILD_COMMAND}" >/dev/null
grep -F 'PUSH_RELAY_READY=1' "${BUILD_COMMAND}" >/dev/null
grep -F '"${dispatcher}" verify' "${BUILD_COMMAND}" >/dev/null
grep -F 'RESULT: FAIL — stopped during ${BUILD_CURRENT_STEP}' "${BUILD_COMMAND}" >/dev/null
grep -F 'RESULT: PASS — rehearsal build and verification completed' "${BUILD_COMMAND}" >/dev/null
grep -F 'failed check: ${failed_check}' \
  "${VERIFY_COMMAND}" >/dev/null
grep -E 'DATABASE_CORE_HOST += "10.10.10.40"' "${PROXMOX_VARIABLES}" >/dev/null
grep -E 'DATABASE_RESPONSE_HOST += "10.10.10.40"' "${PROXMOX_VARIABLES}" >/dev/null
grep -E 'FLOWFORM_EMAIL_FROM_ADDRESS += "no-reply@flow-form.com.au"' "${PROXMOX_VARIABLES}" >/dev/null
# Real mgmt secret is now seeded, so startup validation is ON.
grep -E 'FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP += "true"' "${PROXMOX_VARIABLES}" >/dev/null
# The backend uses the custom issuer for JWKS and the canonical tenant for the
# Management API. Both CONNECT destinations must survive every rebuild.
grep -Fx 'auth.flow-form.com.au' "${REHEARSAL_ALLOWED_DOMAINS}" >/dev/null \
  || { printf 'rehearsal Squid allow-list is missing the Auth0 issuer\n' >&2; exit 1; }
grep -Fx 'dev-3wccg4jx4o5wvedn.au.auth0.com' "${REHEARSAL_ALLOWED_DOMAINS}" >/dev/null \
  || { printf 'rehearsal Squid allow-list is missing the Auth0 Management API tenant\n' >&2; exit 1; }

# --- Wave A: registry-over-HTTPS-through-Squid invariants --------------------
# The registry rides Squid as registry.localstack.test (mirrors ECR-over-HTTPS),
# NOT a plain-HTTP insecure registry pulled direct.
grep -F 'registry.localstack.test:10.10.10.30' "${PROXY_OVERRIDE}" >/dev/null \
  || { printf 'proxy override missing registry.localstack.test extra_hosts\n' >&2; exit 1; }
grep -F 'registry.localstack.test' "${TLS_SHIM_CADDYFILE}" >/dev/null \
  || { printf 'tls-shim Caddyfile missing the registry site block\n' >&2; exit 1; }
grep -E 'BACKEND_IMAGE += "registry.localstack.test/flowform-backend:rehearsal"' "${PROXMOX_VARIABLES}" >/dev/null \
  || { printf 'variables.tf BACKEND_IMAGE not the registry.localstack.test ref\n' >&2; exit 1; }
grep -F 'BACKEND_IMAGE=registry.localstack.test/flowform-backend:rehearsal' "${APP_CLOUD_INIT}" >/dev/null \
  || { printf 'app cloud-init BACKEND_IMAGE not the registry.localstack.test ref\n' >&2; exit 1; }
grep -F '/etc/docker/certs.d/registry.localstack.test/ca.crt' "${APP_CLOUD_INIT}" >/dev/null \
  || { printf 'app cloud-init missing the registry certs.d trust anchor\n' >&2; exit 1; }
# No insecure-registries anywhere: dockerd validates the shim's TLS.
if grep -F 'insecure-registries' "${APP_CLOUD_INIT}" >/dev/null; then
  printf 'app cloud-init still declares insecure-registries\n' >&2; exit 1
fi
# The shared daemon proxy drop-in no longer exempts private CIDRs (pulls ride Squid).
if grep -E 'NO_PROXY=.*10\.0\.0\.0/8' "${REPO_ROOT}/infra/deployment/bootstrap/bootstrap-app.sh" >/dev/null; then
  printf 'bootstrap-app.sh daemon NO_PROXY still exempts 10.0.0.0/8\n' >&2; exit 1
fi

# --- Wave B: enforcement invariants (loopback binds + fixtures firewall) ------
# LocalStack + registry loopback-bound: no off-box direct path; shim is sole ingress.
grep -F '127.0.0.1:4566:4566' "${LOCALSTACK_COMPOSE}" >/dev/null \
  || { printf 'compose.localstack.yml not loopback-bound\n' >&2; exit 1; }
grep -F '127.0.0.1:5000:5000' "${REGISTRY_COMPOSE}" >/dev/null \
  || { printf 'compose.registry.yml not loopback-bound\n' >&2; exit 1; }
if grep -F '10.10.10.30:4566' "${LOCALSTACK_COMPOSE}" >/dev/null; then
  printf 'compose.localstack.yml still publishes 10.10.10.30:4566\n' >&2; exit 1
fi
if grep -F '10.10.10.30:5000' "${REGISTRY_COMPOSE}" >/dev/null; then
  printf 'compose.registry.yml still publishes 10.10.10.30:5000\n' >&2; exit 1
fi
# Shim upstreams point at loopback (LocalStack + registry are loopback-bound).
grep -F 'reverse_proxy http://127.0.0.1:4566' "${TLS_SHIM_CADDYFILE}" >/dev/null \
  || { printf 'tls-shim Caddyfile AWS upstream not loopback\n' >&2; exit 1; }
grep -F 'reverse_proxy http://127.0.0.1:5000' "${TLS_SHIM_CADDYFILE}" >/dev/null \
  || { printf 'tls-shim Caddyfile registry upstream not loopback\n' >&2; exit 1; }
# Fixtures firewall present and admits :443 only from the proxy VM.
grep -F 'flowform-fixtures.nft' "${LOCALSTACK_CLOUD_INIT}" >/dev/null \
  || { printf 'localstack cloud-init missing the fixtures nftables ruleset\n' >&2; exit 1; }
grep -F 'ip saddr 10.10.10.10 tcp dport 443 accept' "${LOCALSTACK_CLOUD_INIT}" >/dev/null \
  || { printf 'fixtures nftables does not admit :443 from the proxy VM only\n' >&2; exit 1; }

# --- Dedicated DB fixture and fail-closed bootstrap invariants ---------------
grep -F 'pull_policy: never' "${DB_COMPOSE}" >/dev/null \
  || { printf 'DB compose permits a runtime image pull\n' >&2; exit 1; }
grep -F 'DATABASE_INIT_TARGET: all' "${DB_COMPOSE}" >/dev/null \
  || { printf 'DB compose does not use the full init path\n' >&2; exit 1; }
grep -F '10.10.10.40:5432:5432/tcp' "${DB_COMPOSE}" >/dev/null \
  || { printf 'DB compose is not bound only to the DB VM address\n' >&2; exit 1; }
grep -F 'ip saddr 10.10.10.20 ip daddr 172.60.0.2 tcp dport 5432 accept' "${DB_CLOUD_INIT}" >/dev/null \
  || { printf 'DB nftables does not enforce the app-to-container path\n' >&2; exit 1; }
grep -F 'ip daddr "${PROXY_PRIVATE_IP}" tcp dport 3128 accept' "${DB_BOOTSTRAP}" >/dev/null \
  || { printf 'DB bootstrap temporary egress is not Squid-only\n' >&2; exit 1; }
grep -F 'DB_BOOTSTRAP_PRIVATE_IP=10.10.10.40' "${PROXY_CLOUD_INIT}" >/dev/null \
  || { printf 'proxy does not admit the rehearsal DB bootstrap source\n' >&2; exit 1; }

printf '[test-localstack-seed] PASS\n'
