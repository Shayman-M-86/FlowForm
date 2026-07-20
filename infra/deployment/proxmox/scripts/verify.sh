#!/usr/bin/env bash
set -Eeuo pipefail

# Verify the live rehearsal enforces the AWS-shaped egress model end to end:
# every fake-AWS + fake-ECR call rides Squid (visible in its access log), the
# direct-bypass paths fail the way an AWS security group would, and the proxy
# serves the API over TLS the committed CA validates.
#
# Reuses logs.sh's jump: temporarily add 10.10.10.1/24 to vmbr10 (only
# if absent), tunnel through the Proxmox host, restore isolation on exit — so a
# Ctrl-C never leaves the private bridge addressed.
#
# Usage:
#   verify.sh              # non-disruptive checks
#   verify.sh --disruptive # also proves AWS calls fail when Squid is down
#
# Env: PVE_HOST, PVE_USER, SSH_KEY, PROXY_LAN_IP, GUEST_USER, plus REPO_ROOT.

log()  { printf '[verify-rehearsal] %s\n' "$*" >&2; }
die()  { printf '[verify-rehearsal] ERROR: %s\n' "$*" >&2; exit 1; }

PVE_HOST="${PVE_HOST:-192.168.68.88}"
PVE_USER="${PVE_USER:-root}"
SSH_KEY="${SSH_KEY:-${HOME}/.ssh/proxmox_codex}"
GUEST_USER="${GUEST_USER:-ec2-user}"
BRIDGE="${BRIDGE:-vmbr10}"
BRIDGE_ADDR="${BRIDGE_ADDR:-10.10.10.1/24}"
PROXY_LAN_IP="${PROXY_LAN_IP:-192.168.70.63}"
API_DOMAIN="${API_DOMAIN:-api.localstack.test}"
SQUID_PROXY_URL="${SQUID_PROXY_URL:-http://10.10.10.10:3128}"

PROXY_IP="10.10.10.10"
APP_IP="10.10.10.20"
FIXTURE_IP="10.10.10.30"
DB_IP="10.10.10.40"
SQUID_CONTAINER="flowform-proxy-squid-1"
# The squid access.log is owned by the in-container squid uid (13); the hardened
# container blocks even root-in-container from reading it, so exec AS uid 13.
SQUID_LOG_UID="${SQUID_LOG_UID:-13}"

DISRUPTIVE=0
[[ "${1:-}" == "--disruptive" ]] && DISRUPTIVE=1

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)}"
CA_CRT="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt"
[[ -f "${CA_CRT}" ]] || die "rehearsal CA not found at ${CA_CRT}"
[[ -f "${SSH_KEY}" ]] || die "ssh key not found at ${SSH_KEY}"

PASS=0
FAIL=0
ok()   { printf '  \033[32mPASS\033[0m %s\n' "$*"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$*"; FAIL=$((FAIL+1)); }

pve_ssh() {
  ssh -i "${SSH_KEY}" -o BatchMode=yes -o ConnectTimeout=8 \
    -o StrictHostKeyChecking=accept-new "${PVE_USER}@${PVE_HOST}" "$@"
}

# guest_ssh <ip> <remote command...>
guest_ssh() {
  local ip="$1"; shift
  ssh -i "${SSH_KEY}" -o BatchMode=yes -o ConnectTimeout=8 \
    -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
    -o "ProxyCommand=ssh -i ${SSH_KEY} -o BatchMode=yes -o StrictHostKeyChecking=accept-new -W %h:%p ${PVE_USER}@${PVE_HOST}" \
    "${GUEST_USER}@${ip}" "$@"
}

BRIDGE_ADDED=0
SQUID_STOPPED=0
cleanup() {
  # Best-effort: restart squid if we stopped it, then drop the bridge address.
  if (( SQUID_STOPPED == 1 )); then
    guest_ssh "${PROXY_IP}" "sudo docker start ${SQUID_CONTAINER}" >/dev/null 2>&1 \
      || log "WARNING: could not restart ${SQUID_CONTAINER} — do it manually"
  fi
  if (( BRIDGE_ADDED == 1 )); then
    pve_ssh "ip address del ${BRIDGE_ADDR} dev ${BRIDGE}" >/dev/null 2>&1 \
      || log "WARNING: could not remove ${BRIDGE_ADDR} from ${BRIDGE} — remove it manually"
  fi
}
trap cleanup EXIT INT TERM HUP

if pve_ssh "ip -4 -o addr show dev ${BRIDGE} | grep -Fq ${BRIDGE_ADDR%%/*}/"; then
  log "${BRIDGE_ADDR} already present; leaving as-is"
else
  pve_ssh "ip address add ${BRIDGE_ADDR} dev ${BRIDGE}" || die "could not add ${BRIDGE_ADDR}"
  BRIDGE_ADDED=1
fi

# unsigned but structurally valid JWT (3 base64url segments, bad kid)
fake_jwt() {
  local h p
  h="$(printf '%s' '{"alg":"RS256","typ":"JWT","kid":"verify-rehearsal"}' | base64 -w0 | tr '+/' '-_' | tr -d '=')"
  p="$(printf '%s' '{"iss":"https://auth.flow-form.com.au/","aud":"https://flowform.auth.api","sub":"t","exp":9999999999}' | base64 -w0 | tr '+/' '-_' | tr -d '=')"
  printf '%s.%s.c2ln' "${h}" "${p}"
}

curl_lan() {  # curl to the proxy LAN IP with committed-CA verification
  curl -sS --connect-timeout 4 --max-time 8 --cacert "${CA_CRT}" \
    --resolve "${API_DOMAIN}:443:${PROXY_LAN_IP}" "$@"
}

echo "== rehearsal egress verification =="

# 1. Health 200 via the proxy LAN, verified TLS.
code="$(curl_lan -o /dev/null -w '%{http_code}' "https://${API_DOMAIN}/api/v1/system/health/ready" || echo 000)"
[[ "${code}" == "200" ]] && ok "health 200 via proxy (verified TLS)" || bad "health expected 200, got ${code}"

# 2. Fake JWT → 401 (not 500): JWKS fetched through Squid, kid mismatch.
code="$(curl_lan -o /dev/null -w '%{http_code}' -X POST \
  -H "Authorization: Bearer $(fake_jwt)" \
  "https://${API_DOMAIN}/api/v1/account/bootstrap-user" || echo 000)"
[[ "${code}" == "401" ]] && ok "fake JWT → 401 (JWKS via Squid)" || bad "fake JWT expected 401, got ${code}"

# 3. Generate fresh egress traffic from the app VM (one CONNECT per SNI + registry).
log "generating egress traffic from the app VM..."
# Each call rides its own SNI → one CONNECT per name. Use explicit per-service
# --endpoint-url so a call cannot silently skip its hostname (belt and braces
# over the AWS_ENDPOINT_URL_* env the bootstrap.env carries).
# Every call is hard-bounded: some LocalStack actions can hang, and traffic-gen
# only needs to OPEN each CONNECT, not complete the API round-trip. `timeout`
# wraps the SDK calls (which have no built-in deadline); curl carries --max-time.
guest_ssh "${APP_IP}" '
  set -a; . /etc/flowform/bootstrap-app.env 2>/dev/null || true; set +a
  timeout 10 aws --cli-connect-timeout 4 --cli-read-timeout 6 --endpoint-url https://ssm.localstack.test ssm get-parameter --name /flowform/nonprod/backend/BACKEND_IMAGE >/dev/null 2>&1 || true
  timeout 10 aws --cli-connect-timeout 4 --cli-read-timeout 6 --endpoint-url https://secretsmanager.localstack.test secretsmanager list-secrets >/dev/null 2>&1 || true
  # kms: a plain health GET through the proxy — its SDK actions can hang, and all
  # we need is one CONNECT to kms:443.
  curl -fsS --connect-timeout 4 --max-time 8 --proxy '"${SQUID_PROXY_URL}"' https://kms.localstack.test/_localstack/health >/dev/null 2>&1 || true
  curl -fsS --connect-timeout 4 --max-time 8 --proxy '"${SQUID_PROXY_URL}"' https://registry.localstack.test/v2/ >/dev/null 2>&1 || true
' >/dev/null 2>&1 || true

# 4. Every fake-AWS + fake-ECR + Auth0 name shows a fresh CONNECT in Squid's log.
squid_log="$(guest_ssh "${PROXY_IP}" \
  "sudo docker exec -u ${SQUID_LOG_UID} ${SQUID_CONTAINER} tail -n 3000 /var/log/squid/access.log" 2>/dev/null || true)"
for name in secretsmanager.localstack.test ssm.localstack.test kms.localstack.test \
            registry.localstack.test auth.flow-form.com.au; do
  if grep -Fq "CONNECT ${name}:443" <<<"${squid_log}"; then
    ok "Squid tunneled ${name}"
  else
    bad "no CONNECT for ${name} in Squid access.log"
  fi
done

# 5. Bypass negatives: direct paths from the app VM must FAIL (ambient proxy off).
#    LocalStack :4566 loopback-bound → refused; shim/registry :443 → nftables drop.
neg() {  # neg <label> <url> — success = curl FAILS to connect (nonzero exit)
  local label="$1" url="$2"
  if guest_ssh "${APP_IP}" "curl -fsS --noproxy '*' --connect-timeout 3 -o /dev/null '${url}'" >/dev/null 2>&1; then
    bad "direct ${label} reachable — bypass not enforced"
  else
    ok "direct ${label} blocked"
  fi
}
neg "LocalStack :4566" "http://10.10.10.30:4566/_localstack/health"
neg "shim ssm :443"    "https://ssm.localstack.test/_localstack/health"
neg "registry :443"    "https://registry.localstack.test/v2/"

# ...and the same names via Squid SUCCEED (positive control).
pos() {  # pos <label> <url> — success = reachable through Squid
  local label="$1" url="$2" rc
  rc="$(guest_ssh "${APP_IP}" "curl -sS --proxy '${SQUID_PROXY_URL}' --connect-timeout 4 -o /dev/null -w '%{http_code}' '${url}'" 2>/dev/null || true)"
  case "${rc}" in
    200|301|302|401|403) ok "${label} via Squid (HTTP ${rc})" ;;
    *)                   bad "${label} via Squid failed (HTTP ${rc:-none})" ;;
  esac
}
pos "shim ssm"  "https://ssm.localstack.test/_localstack/health"
pos "registry"  "https://registry.localstack.test/v2/"

# 6. Dedicated DB reachability and source isolation.
if guest_ssh "${APP_IP}" "timeout 4 bash -c '</dev/tcp/${DB_IP}/5432'" >/dev/null 2>&1; then
  ok "app VM reaches PostgreSQL on VM 240"
else
  bad "app VM cannot reach PostgreSQL on VM 240"
fi

db_blocked_from() {
  local label="$1" source_ip="$2"
  if guest_ssh "${source_ip}" "timeout 3 bash -c '</dev/tcp/${DB_IP}/5432'" >/dev/null 2>&1; then
    bad "${label} reaches PostgreSQL — source isolation failed"
  else
    ok "${label} blocked from PostgreSQL"
  fi
}
db_blocked_from "proxy VM" "${PROXY_IP}"
db_blocked_from "fixtures VM" "${FIXTURE_IP}"
if pve_ssh "timeout 3 bash -c '</dev/tcp/${DB_IP}/5432'" >/dev/null 2>&1; then
  bad "management source reaches PostgreSQL — source isolation failed"
else
  ok "management source blocked from PostgreSQL"
fi

# 7. DB host is fail-closed after bootstrap. It cannot reconnect to Squid or
# any fixture endpoint, and the temporary nftables chain must be empty.
for target in "Squid:${PROXY_IP}:3128" "LocalStack:${FIXTURE_IP}:4566" \
              "registry:${FIXTURE_IP}:443" "internet:1.1.1.1:443"; do
  IFS=: read -r label host port <<<"${target}"
  if guest_ssh "${DB_IP}" "timeout 3 bash -c '</dev/tcp/${host}/${port}'" >/dev/null 2>&1; then
    bad "DB VM reaches ${label} after bootstrap"
  else
    ok "DB VM cannot reach ${label} after bootstrap"
  fi
done
if guest_ssh "${DB_IP}" "sudo nft list chain inet flowform_db bootstrap_egress | grep -Eq ' dport .* accept'" >/dev/null 2>&1; then
  bad "DB bootstrap egress chain still contains an accept rule"
else
  ok "DB bootstrap egress chain is empty"
fi

# 8. The real initialization path produced both DBs, the NOLOGIN owner,
# low-privilege SCRAM app roles, schemas, tables, and grants.
db_psql() {
  local database="$1" sql="$2" quoted_db quoted_sql
  printf -v quoted_db '%q' "${database}"
  printf -v quoted_sql '%q' "${sql}"
  guest_ssh "${DB_IP}" \
    "sudo docker exec flowform-db sh -ec 'export PGPASSWORD=\"\$(cat /run/secrets/DATABASE_INIT_PASSWORD)\"; exec psql -U flowform_rehearsal_init -d \"\$1\" -Atqc \"\$2\"' sh ${quoted_db} ${quoted_sql}"
}

dbs="$(db_psql postgres "SELECT datname FROM pg_database WHERE datname IN ('flowform_core','flowform_response') ORDER BY 1" 2>/dev/null || true)"
[[ "${dbs}" == $'flowform_core\nflowform_response' ]] \
  && ok "both rehearsal databases were initialized" \
  || bad "expected both rehearsal databases, got: ${dbs:-none}"

roles="$(db_psql postgres "SELECT rolname || ':' || rolcanlogin || ':' || rolsuper || ':' || rolcreatedb || ':' || rolcreaterole || ':' || rolreplication || ':' || rolbypassrls || ':' || coalesce(rolpassword LIKE 'SCRAM-SHA-256%', false) FROM pg_authid WHERE rolname IN ('flowform_owner','flowform_core_app','flowform_response_app') ORDER BY 1" 2>/dev/null || true)"
grep -Fqx 'flowform_owner:false:false:false:false:false:false:false' <<<"${roles}" \
  && ok "flowform_owner is NOLOGIN" || bad "flowform_owner contract failed"
for role in flowform_core_app flowform_response_app; do
  grep -Fqx "${role}:true:false:false:false:false:false:true" <<<"${roles}" \
    && ok "${role} is low-privilege with SCRAM credentials" \
    || bad "${role} privilege or SCRAM contract failed"
done

for contract in "flowform_core:core_app:flowform_core_app" \
                "flowform_response:response_app:flowform_response_app"; do
  IFS=: read -r database schema role <<<"${contract}"
  schema_result="$(db_psql "${database}" "SELECT n.nspname || ':' || r.rolname || ':' || has_schema_privilege('${role}', n.oid, 'USAGE') || ':' || (SELECT count(*) > 0 FROM pg_class c WHERE c.relnamespace=n.oid) || ':' || (SELECT bool_and(has_table_privilege('${role}', quote_ident(schemaname) || '.' || quote_ident(tablename), 'SELECT,INSERT,UPDATE,DELETE')) FROM pg_tables WHERE schemaname='${schema}') FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner WHERE n.nspname='${schema}'" 2>/dev/null || true)"
  [[ "${schema_result}" == "${schema}:flowform_owner:true:true:true" ]] \
    && ok "${database}.${schema} ownership, grants, and schema objects initialized" \
    || bad "${database}.${schema} init contract failed (${schema_result:-none})"
done

if guest_ssh "${DB_IP}" "sudo journalctl -u flowform-db.service --no-pager | grep -Eq 'Pulling|Pulled newer image|pull access denied'" >/dev/null 2>&1; then
  bad "DB service log indicates a runtime image pull"
else
  ok "DB service performed no runtime PostgreSQL pull"
fi

# 9. Disruptive: AWS calls from the app VM fail when Squid is down.
if (( DISRUPTIVE == 1 )); then
  log "--disruptive: stopping Squid to prove fail-closed..."
  guest_ssh "${PROXY_IP}" "sudo docker stop ${SQUID_CONTAINER}" >/dev/null 2>&1 && SQUID_STOPPED=1
  rc="$(guest_ssh "${APP_IP}" "curl -sS --proxy '${SQUID_PROXY_URL}' --connect-timeout 4 -o /dev/null -w '%{http_code}' https://registry.localstack.test/v2/ 2>/dev/null || true" 2>/dev/null || true)"
  rc="${rc:-000}"
  [[ "${rc}" == "000" ]] && ok "egress fails with Squid down" || bad "egress still worked (HTTP ${rc}) with Squid stopped"
  guest_ssh "${PROXY_IP}" "sudo docker start ${SQUID_CONTAINER}" >/dev/null 2>&1 && SQUID_STOPPED=0
  # wait for Squid to accept again
  for _ in $(seq 1 15); do
    rc="$(guest_ssh "${APP_IP}" "curl -sS --proxy '${SQUID_PROXY_URL}' --connect-timeout 3 -o /dev/null -w '%{http_code}' https://registry.localstack.test/v2/ 2>/dev/null || true" 2>/dev/null || true)"
    rc="${rc:-000}"
    [[ "${rc}" != "000" ]] && break; sleep 2
  done
  [[ "${rc}" != "000" ]] && ok "egress restored after Squid restart" || bad "egress did not recover after Squid restart"
fi

echo "== ${PASS} passed, ${FAIL} failed =="
(( FAIL == 0 )) || exit 1
