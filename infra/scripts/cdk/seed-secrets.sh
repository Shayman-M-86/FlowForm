#!/usr/bin/env bash
set -euo pipefail

# Pushes real secret values from infra/cdk/.env.<env> into the two Secrets
# Manager entries security_stack.py creates (flowform/<env>/app-secrets and
# flowform/<env>/db-secrets). CDK only provisions the secrets with generated
# placeholder values — it never seeds real values, so this script is the
# out-of-band step that fills them in.
#
# Dry run by default: prints the AWS CLI calls it would make without sending
# anything. Pass --send to actually call Secrets Manager — you'll still be
# asked to confirm y/n for each secret before it's written.
#
# Usage:
#   scripts/seed-secrets.sh [--env dev] [--send]

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
CDK_ROOT="$(cd "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd)"

ENV_NAME="dev"
SEND=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENV_NAME="$2"
      shift 2
      ;;
    --send)
      SEND=true
      shift
      ;;
    *)
      echo "error: unknown argument '$1'" >&2
      exit 1
      ;;
  esac
done

ENV_FILE="$CDK_ROOT/.env.$ENV_NAME"

if ! command -v aws >/dev/null 2>&1; then
  echo "error: 'aws' CLI not found on PATH." >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "error: $ENV_FILE not found. Copy .env.dev.example to .env.$ENV_NAME and fill in real values first." >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

required_vars=(
  APP_SECRET_KEY
  AUTH0_MGMT_SECRET
  LINKAGE_SECRET
  DB_CORE_APP_PASSWORD
  DB_RESPONSE_APP_PASSWORD
)
for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "error: $var is empty in $ENV_FILE" >&2
    exit 1
  fi
done

app_secrets_json=$(printf '{"app_secret_key":%s,"auth0_mgmt_secret":%s,"linkage_secret":%s}' \
  "$(printf '%s' "$APP_SECRET_KEY" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
  "$(printf '%s' "$AUTH0_MGMT_SECRET" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
  "$(printf '%s' "$LINKAGE_SECRET" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")

db_secrets_json=$(printf '{"db_core_app_password":%s,"db_response_app_password":%s}' \
  "$(printf '%s' "$DB_CORE_APP_PASSWORD" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
  "$(printf '%s' "$DB_RESPONSE_APP_PASSWORD" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")

app_secret_id="flowform/$ENV_NAME/app-secrets"
db_secret_id="flowform/$ENV_NAME/db-secrets"

confirm() {
  local prompt="$1"
  local reply
  read -r -p "$prompt [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

seed_one() {
  local secret_id="$1"
  local secret_json="$2"

  if [[ "$SEND" == false ]]; then
    echo "aws secretsmanager put-secret-value --secret-id '$secret_id' --secret-string '<${#secret_json} bytes>'"
    return
  fi

  if ! confirm "Seed $secret_id? This overwrites its current value in AWS."; then
    echo "Skipped $secret_id."
    return
  fi

  echo "Seeding $secret_id ..."
  aws secretsmanager put-secret-value --secret-id "$secret_id" --secret-string "$secret_json" >/dev/null
  echo "Done: $secret_id."
}

if [[ "$SEND" == false ]]; then
  echo "DRY RUN (no changes made) — re-run with --send to apply."
  echo
fi

seed_one "$app_secret_id" "$app_secrets_json"
seed_one "$db_secret_id" "$db_secrets_json"
