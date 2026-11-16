#!/usr/bin/env bash
set -euo pipefail

# seed-secrets.sh compares each key with AWS before writing. A mock `aws` keeps
# secrets as JSON files so every path can be exercised without real AWS.

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT="${REPO_ROOT}/infra/deployment/aws/scripts/seed-secrets.sh"
TEST_DIR="$(mktemp -d)"
MOCK_BIN="${TEST_DIR}/bin"
STORE="${TEST_DIR}/store"
AWS_LOG="${TEST_DIR}/aws.log"
OUT="${TEST_DIR}/out.log"

cleanup() { rm -rf -- "${TEST_DIR}"; }
trap cleanup EXIT
mkdir -p "${MOCK_BIN}" "${STORE}"

cat >"${MOCK_BIN}/aws" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%q ' "$@" >>"${AWS_LOG}"; printf '\n' >>"${AWS_LOG}"
if [[ "$1" == sts ]]; then printf '111122223333\tarn:aws:iam::111122223333:user/test\n'; exit 0; fi
shift 3 # secretsmanager --region <region>
cmd="$1"; shift
id=""; file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --secret-id) id="$2"; shift 2 ;;
    --secret-string) file="${2#file://}"; shift 2 ;;
    *) shift ;;
  esac
done
path="${STORE}/${id//\//_}.json"
case "$cmd" in
  describe-secret) [[ -f "$path" ]] ;;
  get-secret-value) cat "$path" ;;
  put-secret-value) cp "$file" "$path"; echo "v-new" ;;
esac
EOF
chmod +x "${MOCK_BIN}/aws"
export AWS_LOG STORE PATH="${MOCK_BIN}:${PATH}"

APP="${STORE}/flowform_nonprod_app-secrets.json"
DB="${STORE}/flowform_nonprod_db-secrets.json"
ENV_FILE="${TEST_DIR}/.env.dev"
export SEED_SECRETS_ENV_FILE="${ENV_FILE}"

reset_store() {
  printf '%s' '{"app_secret_key":"aws-app-secret","auth0_mgmt_secret":"aws-auth0-secret","legacy_key":"aws-legacy"}' >"$APP"
  printf '%s' '{"db_core_app_password":"aws-core-pw","db_response_app_password":"aws-response-pw"}' >"$DB"
  : >"${AWS_LOG}"
}

write_env() { printf '%s\n' "$@" >"${ENV_FILE}"; }

assert_no_leak() {
  local value
  for value in aws-app-secret aws-auth0-secret aws-legacy aws-core-pw aws-response-pw local-openai-key local-app-secret; do
    ! grep -Fq "$value" "$OUT" "${AWS_LOG}" || { echo "FAIL: secret value '$value' leaked" >&2; exit 1; }
  done
}

puts() { grep -c 'put-secret-value' "${AWS_LOG}" || true; }

# 1. Dry run: plan only, no prompts, no writes.
reset_store
write_env 'APP_SECRET_KEY=' 'AUTH0_MGMT_SECRET=' 'OPENAI_API_KEY=local-openai-key'
"${SCRIPT}" --env dev >"$OUT" 2>&1
grep -Fq 'DRY RUN' "$OUT"
grep -Fq 'reuse      app_secret_key' "$OUT"
grep -Fq 'add        openai_api_key' "$OUT"
grep -Fq 'preserved  legacy_key' "$OUT"
grep -Fq 'No changes for flowform/nonprod/db-secrets' "$OUT"
[[ "$(puts)" == 0 ]]
assert_no_leak

# 2. Send: reuse blanks, add the new key, keep unmanaged keys, verify read-back.
reset_store
printf '%s\n' y '' '' y y '' '' | "${SCRIPT}" --env dev --send >"$OUT" 2>&1
grep -Fq 'verified by read-back' "$OUT"
[[ "$(puts)" == 1 ]]
[[ "$(jq -r .openai_api_key "$APP")" == local-openai-key ]]
[[ "$(jq -r .app_secret_key "$APP")" == aws-app-secret ]]
[[ "$(jq -r .legacy_key "$APP")" == aws-legacy ]]
assert_no_leak

# 3. A different local value is NOT replaced unless the key name is typed.
reset_store
write_env 'APP_SECRET_KEY=local-app-secret' 'AUTH0_MGMT_SECRET=' 'OPENAI_API_KEY='
printf '%s\n' y nope '' '' '' '' | "${SCRIPT}" --env dev --send >"$OUT" 2>&1
grep -Fq 'keep       app_secret_key' "$OUT"
[[ "$(puts)" == 0 ]]
[[ "$(jq -r .app_secret_key "$APP")" == aws-app-secret ]]
assert_no_leak

# 4. Typing the key name replaces it.
reset_store
printf '%s\n' y app_secret_key '' y '' '' | "${SCRIPT}" --env dev --send >"$OUT" 2>&1
[[ "$(jq -r .app_secret_key "$APP")" == local-app-secret ]]
[[ "$(jq -r .auth0_mgmt_secret "$APP")" == aws-auth0-secret ]]
assert_no_leak

# 5. Closed input aborts before any write.
reset_store
write_env 'OPENAI_API_KEY=local-openai-key'
if "${SCRIPT}" --env dev --send </dev/null >"$OUT" 2>&1; then echo "FAIL: closed input did not abort" >&2; exit 1; fi
grep -Fq 'aborting without writing' "$OUT"
[[ "$(puts)" == 0 ]]

# 6. A required key blank on both sides aborts.
reset_store
printf '%s' '{"auth0_mgmt_secret":"aws-auth0-secret"}' >"$APP"
write_env 'APP_SECRET_KEY='
if "${SCRIPT}" --env dev >"$OUT" 2>&1; then echo "FAIL: missing required key accepted" >&2; exit 1; fi
grep -Fq 'app_secret_key is required but blank' "$OUT"

# 7. A non-JSON secret is never overwritten.
reset_store
printf '%s' 'not-json' >"$APP"
if "${SCRIPT}" --env dev >"$OUT" 2>&1; then echo "FAIL: non-JSON secret accepted" >&2; exit 1; fi
grep -Fq 'refusing to overwrite' "$OUT"

echo "[test-seed-secrets] PASS"
