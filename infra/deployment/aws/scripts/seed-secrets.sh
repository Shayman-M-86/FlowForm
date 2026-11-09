#!/usr/bin/env bash
set -euo pipefail

# Pushes real secret values from infra/deployment/aws/cdk/.env.<env> into the
# two multi-key Secrets Manager entries security_stack.py creates for the
# environment's security scope:
#
#   flowform/<scope>/app-secrets  {app_secret_key, auth0_mgmt_secret}
#   flowform/<scope>/db-secrets   {db_core_app_password, db_response_app_password}
#
# dev and staging share the nonprod scope; prod uses prod. CDK only provisions
# placeholders, so this is the out-of-band step that fills them in. The linkage,
# observability and tunnel secrets have their own formats and seed scripts.
#
# Dry run by default: prints what it would write without sending anything. Pass
# --send to write; each secret still asks for y/n confirmation. Values reach
# the AWS CLI through mode-0600 temporary files, never as arguments.
#
# Usage:
#   infra/deployment/aws/scripts/seed-secrets.sh [--env dev|staging|prod] [--send]

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
CDK_ROOT="$(cd "$SCRIPT_DIR/../cdk" >/dev/null 2>&1 && pwd)"
AWS_REGION="${AWS_REGION:-ap-southeast-2}"

ENV_NAME="dev"
SEND=false
TEMP_DIR=""

cleanup() {
  if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
    rm -rf -- "$TEMP_DIR"
  fi
}
trap cleanup EXIT

die() {
  echo "error: $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      [[ $# -ge 2 ]] || die "--env requires a value"
      ENV_NAME="$2"
      shift 2
      ;;
    --send)
      SEND=true
      shift
      ;;
    *)
      die "unknown argument '$1'"
      ;;
  esac
done

case "$ENV_NAME" in
  dev|staging) SCOPE="nonprod" ;;
  prod) SCOPE="prod" ;;
  *) die "unsupported environment: $ENV_NAME" ;;
esac

command -v aws >/dev/null 2>&1 || die "'aws' CLI not found on PATH."
command -v jq >/dev/null 2>&1 || die "'jq' not found on PATH."

ENV_FILE="$CDK_ROOT/.env.$ENV_NAME"
[[ -f "$ENV_FILE" ]] \
  || die "$ENV_FILE not found. Copy .env.dev.example to .env.$ENV_NAME and fill in real values first."

set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

for var in APP_SECRET_KEY AUTH0_MGMT_SECRET DB_CORE_APP_PASSWORD DB_RESPONSE_APP_PASSWORD; do
  [[ -n "${!var:-}" ]] || die "$var is empty in $ENV_FILE"
done

TEMP_DIR="$(mktemp -d)"
chmod 700 "$TEMP_DIR"
umask 077
jq -n --arg app_secret_key "$APP_SECRET_KEY" --arg auth0_mgmt_secret "$AUTH0_MGMT_SECRET" \
  '{app_secret_key: $app_secret_key, auth0_mgmt_secret: $auth0_mgmt_secret}' > "$TEMP_DIR/app-secrets.json"
jq -n --arg core "$DB_CORE_APP_PASSWORD" --arg response "$DB_RESPONSE_APP_PASSWORD" \
  '{db_core_app_password: $core, db_response_app_password: $response}' > "$TEMP_DIR/db-secrets.json"
unset APP_SECRET_KEY AUTH0_MGMT_SECRET DB_CORE_APP_PASSWORD DB_RESPONSE_APP_PASSWORD

confirm() {
  local reply
  read -r -p "$1 [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

seed_one() { # $1 = secret name suffix, $2 = extra warning (optional)
  local secret_id="flowform/$SCOPE/$1" file="$TEMP_DIR/$1.json"

  aws secretsmanager describe-secret --region "$AWS_REGION" --secret-id "$secret_id" >/dev/null \
    || die "$secret_id does not exist; deploy the security stack first."

  if [[ "$SEND" == false ]]; then
    echo "would write $secret_id ($(jq -r 'keys | join(", ")' "$file"))"
    return
  fi

  [[ -n "${2:-}" ]] && echo "note: $2"
  if ! confirm "Seed $secret_id? This overwrites its current value in AWS."; then
    echo "Skipped $secret_id."
    return
  fi

  aws secretsmanager put-secret-value --region "$AWS_REGION" --secret-id "$secret_id" \
    --secret-string "file://$file" >/dev/null
  echo "Done: $secret_id."
}

if [[ "$SEND" == false ]]; then
  echo "DRY RUN (no changes made) — re-run with --send to apply."
  echo
fi

seed_one app-secrets
seed_one db-secrets "an initialized database keeps the role passwords it was created with; changing db-secrets alone does not rotate them, and the app would then fail to connect."
