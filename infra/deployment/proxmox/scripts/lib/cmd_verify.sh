#!/usr/bin/env bash
# `rehearsal verify` — assert the live rehearsal enforces the AWS-shaped egress
# model end to end: every fake-AWS + fake-ECR call rides Squid (visible in its
# access log), the direct-bypass paths fail the way an AWS security group would,
# and the proxy serves the API over TLS the committed CA validates.
#
# Usage:
#   rehearsal verify              # non-disruptive checks
#   rehearsal verify --disruptive # also proves AWS calls fail when Squid is down

cmd_verify_main() {
  local DISRUPTIVE=0
  case "${1:-}" in
    "") ;;
    --disruptive) DISRUPTIVE=1; shift ;;
    -h|--help)
      printf '%s\n' 'Usage: rehearsal verify [--disruptive]' \
        'Verify the live rehearsal egress, TLS, service, and database contracts.'
      return 0
      ;;
    *) die "unknown verify argument: $1" ;;
  esac
  [[ $# -eq 0 ]] || die "verify accepts only --disruptive"

  local PROXY_LAN_IP="${PROXY_LAN_IP:-192.168.70.63}"
  local API_DOMAIN="${API_DOMAIN:-api.localstack.test}"
  local SQUID_PROXY_URL="${SQUID_PROXY_URL:-http://10.10.10.10:3128}"

  local PROXY_IP FIXTURE_IP APP_IP DB_IP
  PROXY_IP="$(rehearsal_ip proxy)"
  APP_IP="$(rehearsal_ip app)"
  FIXTURE_IP="$(rehearsal_ip fixtures)"
  DB_IP="$(rehearsal_ip db)"
  local SQUID_CONTAINER="flowform-proxy-squid-1"
  # The squid access.log is owned by the in-container squid uid (13); the
  # hardened container blocks even root-in-container from reading it, so exec
  # AS uid 13.
  local SQUID_LOG_UID="${SQUID_LOG_UID:-13}"

  local REPO_ROOT CA_CRT
  REPO_ROOT="${REPO_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../../.." && pwd)}"
  CA_CRT="${REPO_ROOT}/infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt"
  rehearsal_preflight
  [[ -f "${CA_CRT}" ]] || die "rehearsal CA not found at ${CA_CRT}"

  local PASS=0 FAIL=0 VERIFY_STARTED_AT
  local -a VERIFY_FAILURES=()
  VERIFY_STARTED_AT="$(date +%s)"
  ok()  { rehearsal_result PASS "$*"; PASS=$((PASS+1)); }
  bad() {
    rehearsal_result FAIL "$*"
    VERIFY_FAILURES+=("$*")
    FAIL=$((FAIL+1))
  }

  local SQUID_STOPPED=0
  cleanup() {
    # Best-effort: restart squid if we stopped it, then drop the bridge address.
    if (( SQUID_STOPPED == 1 )); then
      guest_ssh "${PROXY_IP}" "sudo docker start ${SQUID_CONTAINER}" >/dev/null 2>&1 \
        || log "WARNING: could not restart ${SQUID_CONTAINER} — do it manually"
    fi
    rehearsal_bridge_down
  }
  cleanup_exit() {
    local status=$?
    trap - EXIT INT TERM HUP
    cleanup
    exit "${status}"
  }
  cleanup_signal() {
    trap - EXIT INT TERM HUP
    cleanup
    exit 130
  }
  trap cleanup_exit EXIT
  trap cleanup_signal INT TERM HUP
  rehearsal_bridge_up

  # unsigned but structurally valid JWT (3 base64url segments, bad kid)
  fake_jwt() {
    local h p
    h="$(printf '%s' '{"alg":"RS256","typ":"JWT","kid":"verify-rehearsal"}' | base64 -w0 | tr '+/' '-_' | tr -d '=')"
    p="$(printf '%s' '{"iss":"https://auth.flow-form.com.au/","aud":"https://flowform.auth.api","sub":"t","exp":9999999999}' | base64 -w0 | tr '+/' '-_' | tr -d '=')"
    printf '%s.%s.c2ln' "${h}" "${p}"
  }

  local LAN_VIA_PVE=0
  curl_lan() {  # curl to the proxy LAN IP; fall back through the proxy guest
    local local_output
    if ((LAN_VIA_PVE == 0)) && local_output="$(curl -sS --connect-timeout 4 --max-time 8 \
      --cacert "${CA_CRT}" --resolve "${API_DOMAIN}:443:${PROXY_LAN_IP}" "$@")"; then
      printf '%s' "${local_output}"
      return 0
    fi
    # From WSL/NAT the management host has no route to the proxy's LAN NIC (the
    # same limitation the certificate check above works around). The proxy guest
    # does reach its own LAN interface, so run the LAN curl from there. The
    # committed CA is already installed in the guest's trust store (cloud-init
    # update-ca-trust), so verified TLS still holds — no -k.
    LAN_VIA_PVE=1
    local remote
    printf -v remote '%q ' curl -sS --connect-timeout 4 --max-time 8 \
      --resolve "${API_DOMAIN}:443:${PROXY_LAN_IP}" "$@"
    guest_ssh "${PROXY_IP}" "${remote}"
  }

  phase "running rehearsal egress verification"

  local code certificate
  # Validate from the proxy guest itself. The PVE management host is not
  # guaranteed to have a route to the proxy's LAN NIC, which previously turned
  # a management-routing limitation into a false certificate failure.
  certificate="$(guest_ssh "${PROXY_IP}" "timeout 8 openssl s_client -connect '${PROXY_LAN_IP}:443' -servername '${API_DOMAIN}' </dev/null 2>/dev/null" \
    | openssl x509 -outform PEM 2>/dev/null || true)"
  if [[ -n "${certificate}" ]] && printf '%s\n' "${certificate}" \
      | openssl verify -CAfile "${CA_CRT}" >/dev/null 2>&1; then
    ok "proxy LAN certificate validates against the committed rehearsal CA"
  else
    bad "proxy LAN certificate did not validate against the committed rehearsal CA"
  fi

  # 1. Health 200 via the proxy LAN, verified TLS.
  if ! code="$(curl_lan -o /dev/null -w '%{http_code}' "https://${API_DOMAIN}/api/v1/system/health/ready")"; then
    code=000
  fi
  [[ "${code}" == "200" ]] && ok "health 200 via proxy" || bad "health expected 200, got ${code}"

  # Trace timelines and JWT validation require both hosts to share a trustworthy
  # clock. The proxy synchronizes externally and serves NTP only on vmbr10; the
  # isolated app must select that private source and settle within 50 ms.
  if guest_ssh "${PROXY_IP}" \
      "chronyc -n waitsync 10 0.05 0.0 1 >/dev/null 2>&1 \
       && ss -H -lun | awk '\$4 ~ /:123$/ {
            seen_private = seen_private || \$4 == \"10.10.10.10:123\"
            unexpected = unexpected || (\$4 != \"10.10.10.10:123\" && \$4 != \"[::1]:123\")
          }
          END { exit !(seen_private && !unexpected) }'" >/dev/null 2>&1; then
    ok "proxy clock synchronized and serving private NTP"
  else
    bad "proxy clock is unsynchronized or not serving 10.10.10.10:123/udp"
  fi

  if guest_ssh "${APP_IP}" \
      "chronyc -n waitsync 10 0.05 0.0 1 >/dev/null 2>&1 \
       && chronyc -n sources | awk '\$1 == \"^*\" && \$2 == \"${PROXY_IP}\" { found=1 } END { exit !found }'" \
      >/dev/null 2>&1; then
    ok "app clock synchronized from proxy private NTP"
  else
    bad "app clock is unsynchronized or did not select ${PROXY_IP} as its NTP source"
  fi

  # 2. Fake JWT → 401 (not 500): JWKS fetched through Squid, kid mismatch.
  if ! code="$(curl_lan -o /dev/null -w '%{http_code}' -X POST \
    -H "Authorization: Bearer $(fake_jwt)" \
    "https://${API_DOMAIN}/api/v1/account/bootstrap-user")"; then
    code=000
  fi
  [[ "${code}" == "401" ]] && ok "fake JWT → 401 (JWKS via Squid)" || bad "fake JWT expected 401, got ${code}"

  # 3. Generate fresh egress traffic from the app VM (one CONNECT per SNI + registry).
  log "generating egress traffic from the app VM..."
  guest_ssh "${APP_IP}" '
    set -a; . /etc/flowform/bootstrap-app.env 2>/dev/null || true; set +a
    timeout 10 aws --cli-connect-timeout 4 --cli-read-timeout 6 --endpoint-url https://ssm.localstack.test ssm get-parameter --name /flowform/nonprod/backend/BACKEND_IMAGE >/dev/null 2>&1 || true
    timeout 10 aws --cli-connect-timeout 4 --cli-read-timeout 6 --endpoint-url https://secretsmanager.localstack.test secretsmanager list-secrets >/dev/null 2>&1 || true
    curl -fsS --connect-timeout 4 --max-time 8 --proxy '"${SQUID_PROXY_URL}"' https://kms.localstack.test/_localstack/health >/dev/null 2>&1 || true
    curl -fsS --connect-timeout 4 --max-time 8 --proxy '"${SQUID_PROXY_URL}"' https://registry.localstack.test/v2/ >/dev/null 2>&1 || true
    curl -fsS --connect-timeout 4 --max-time 8 --proxy '"${SQUID_PROXY_URL}"' https://auth.flow-form.com.au/.well-known/openid-configuration >/dev/null 2>&1 || true
  ' >/dev/null 2>&1 || true

  # 4. Every fake-AWS + fake-ECR + Auth0 name shows a fresh CONNECT in Squid's log.
  local squid_log name
  squid_log="$(guest_ssh "${PROXY_IP}" \
    "sudo docker exec -u ${SQUID_LOG_UID} ${SQUID_CONTAINER} tail -n 3000 /var/log/squid/access.log" 2>/dev/null || true)"
  for name in secretsmanager.localstack.test ssm.localstack.test kms.localstack.test \
              registry.localstack.test auth.flow-form.com.au; do
    # Squid logs via the custom flowform_access logfmt (see squid.conf), so a
    # CONNECT tunnel serialises as `method=CONNECT path="host:443"`, NOT the
    # native `CONNECT host:443` request line.
    if grep -Fq "method=CONNECT path=\"${name}:443\"" <<<"${squid_log}"; then
      ok "Squid tunneled ${name}"
    else
      bad "no CONNECT for ${name} in Squid access.log"
    fi
  done

  # 5. Bypass negatives: direct paths from the app VM must FAIL (ambient proxy off).
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

  # 7. DB host is fail-closed after bootstrap.
  local target label host port
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

  local dbs roles role
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

  local contract database schema schema_result
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
    local rc
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

  local verify_elapsed=$(( $(date +%s) - VERIFY_STARTED_AT )) failed_check
  phase "verification summary"
  log "checks: $((PASS + FAIL)) total | ${PASS} passed | ${FAIL} failed | elapsed: ${verify_elapsed}s"
  if (( FAIL == 0 )); then
    success "RESULT: PASS — rehearsal contracts verified"
  else
    error "RESULT: FAIL — rehearsal is not fully verified"
    for failed_check in "${VERIFY_FAILURES[@]}"; do
      error "failed check: ${failed_check}"
    done
    log "next: fix the failed check(s), then rerun 'infra/deployment/proxmox/scripts/rehearsal verify'"
  fi
  local status=0
  (( FAIL == 0 )) || status=1
  # Run while this function's local proxy/squid state is still in scope.
  trap - EXIT INT TERM HUP
  cleanup
  return "${status}"
}
