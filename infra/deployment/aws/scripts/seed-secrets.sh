#!/usr/bin/env bash
set -euo pipefail

# Seed the two multi-key Secrets Manager entries security_stack.py creates for
# the environment's security scope, comparing every key against what AWS
# already holds before changing anything:
#
#   flowform/<scope>/app-secrets  {app_secret_key, auth0_mgmt_secret, [openai_api_key]}
#   flowform/<scope>/db-secrets   {db_core_app_password, db_response_app_password}
#
# Values come from infra/deployment/aws/cdk/.env.<env> (APP_SECRET_KEY,
# AUTH0_MGMT_SECRET, OPENAI_API_KEY, DB_CORE_APP_PASSWORD,
# DB_RESPONSE_APP_PASSWORD). Any of them may be left blank. Per key:
#
#   env file  AWS            action
#   set       empty          add      (asks to confirm)
#   set       same value     unchanged
#   set       different      replace  (you must type the key name)
#   blank     set            reuse the AWS value (asks; required keys abort on "no",
#                            optional keys can be removed by typing the key name)
#   blank     empty          required: abort / optional: skip
#
# Keys in AWS that this script does not manage are always preserved. Each secret
# shows a plan and needs a final confirmation, then is read back and verified.
#
# dev and staging share the nonprod scope; prod uses prod. CDK only provisions
# placeholders. The linkage, observability and tunnel secrets have their own
# formats and seed scripts.
#
# Dry run by default: prints the plan (key names and actions only) without
# prompting or writing. --send prompts and writes. Secret values are never
# printed and never passed as command-line arguments; they move through
# mode-0600 temporary files. If input ends or a prompt cannot be answered, the
# script aborts without writing.
#
# Usage:
#   infra/deployment/aws/scripts/seed-secrets.sh [--env dev|staging|prod] [--send]

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
CDK_ROOT="$(cd "$SCRIPT_DIR/../cdk" >/dev/null 2>&1 && pwd)"
AWS_REGION="${AWS_REGION:-ap-southeast-2}"

ENV_NAME="dev"
SEND=false
TEMP_DIR=""

APP_REQUIRED_KEYS=(app_secret_key auth0_mgmt_secret)
APP_OPTIONAL_KEYS=(openai_api_key)
DB_REQUIRED_KEYS=(db_core_app_password db_response_app_password)

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

ENV_FILE="${SEED_SECRETS_ENV_FILE:-$CDK_ROOT/.env.$ENV_NAME}"
[[ -f "$ENV_FILE" ]] \
  || die "$ENV_FILE not found. Copy .env.dev.example to .env.$ENV_NAME first (secret values may stay blank to reuse AWS values)."

TEMP_DIR="$(mktemp -d)"
chmod 700 "$TEMP_DIR"
umask 077
mkdir -p "$TEMP_DIR/local"

# Load the env file, move each non-empty secret value into its own 0600 file,
# then drop it from the environment so it cannot leak into child processes.
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a
for key in "${APP_REQUIRED_KEYS[@]}" "${APP_OPTIONAL_KEYS[@]}" "${DB_REQUIRED_KEYS[@]}"; do
  var="${key^^}"
  if [[ -n "${!var:-}" ]]; then
    printf '%s' "${!var}" > "$TEMP_DIR/local/$key"
  fi
  unset "$var"
done

# ── Prompts ─────────────────────────────────────────────────────────────────
# Prompts read stdin. End of input is never treated as consent.

ask() { # $1 = prompt ; prints the answer
  local reply
  if ! read -r -p "$1 " reply; then
    echo >&2
    die "no answer received (input closed); aborting without writing anything."
  fi
  printf '%s' "$reply"
}

confirm() { # $1 = question ; default No
  local reply
  reply="$(ask "$1 [y/N]")"
  [[ "$reply" =~ ^[Yy]$ ]]
}

confirm_default_yes() { # $1 = question ; default Yes
  local reply
  reply="$(ask "$1 [Y/n]")"
  [[ ! "$reply" =~ ^[Nn]$ ]]
}

confirm_typed() { # $1 = word the user must type exactly
  local reply
  reply="$(ask "Type '$1' to confirm (anything else cancels):")"
  [[ "$reply" == "$1" ]]
}

# ── AWS helpers ─────────────────────────────────────────────────────────────

aws_sm() {
  aws secretsmanager --region "$AWS_REGION" "$@"
}

# Write the current SecretString of $1 to file $2 and require a JSON object.
fetch_current() {
  local secret_id="$1" out="$2"
  aws_sm describe-secret --secret-id "$secret_id" >/dev/null \
    || die "$secret_id does not exist or is not readable; deploy the security stack and check your AWS session."
  aws_sm get-secret-value --secret-id "$secret_id" --query SecretString --output text > "$out" \
    || die "could not read the current value of $secret_id."
  jq -e 'type == "object"' "$out" >/dev/null 2>&1 \
    || die "$secret_id does not hold a JSON object; refusing to overwrite it. Inspect it in the AWS console first."
}

set_key() { # $1 = json file ; $2 = key ; $3 = value file (value never on argv)
  jq --arg k "$2" --rawfile v "$3" '.[$k] = $v' "$1" > "$1.tmp" && mv "$1.tmp" "$1"
}

# ── Planning ────────────────────────────────────────────────────────────────

# Builds $TEMP_DIR/<suffix>.new.json from the current value and records the
# per-key actions in PLAN_LINES. Sets CHANGED=true when anything differs.
plan_secret() { # $1 = suffix ; $2 = "required keys" ; $3 = "optional keys"
  local suffix="$1" current="$TEMP_DIR/$1.current.json" next="$TEMP_DIR/$1.new.json"
  local -a required=() optional=()
  read -r -a required <<<"$2"
  [[ -n "${3:-}" ]] && read -r -a optional <<<"$3"
  cp "$current" "$next"
  PLAN_LINES=()
  CHANGED=false

  local key kind local_file aws_file has_local has_aws
  for key in "${required[@]}" "${optional[@]}"; do
    kind=required
    [[ " ${optional[*]} " == *" $key "* ]] && kind=optional
    local_file="$TEMP_DIR/local/$key"
    aws_file="$TEMP_DIR/$suffix.aws.$key"
    jq -j --arg k "$key" '.[$k] // "" | if type == "string" then . else tojson end' "$current" > "$aws_file"
    has_local=false; [[ -s "$local_file" ]] && has_local=true
    has_aws=false; [[ -s "$aws_file" ]] && has_aws=true

    if $has_local && ! $has_aws; then
      if [[ "$SEND" != true ]] || confirm "Add a NEW value for $key ($kind) to flowform/$SCOPE/$suffix?"; then
        set_key "$next" "$key" "$local_file"
        PLAN_LINES+=("add        $key")
        CHANGED=true
      elif [[ "$kind" == required ]]; then
        die "$key is required and AWS has no value for it; cannot continue without adding it."
      else
        PLAN_LINES+=("skip       $key (not added)")
      fi
    elif $has_local && cmp -s "$local_file" "$aws_file"; then
      PLAN_LINES+=("unchanged  $key")
    elif $has_local; then
      [[ "$SEND" == true ]] \
        && echo "warning: AWS already holds a DIFFERENT value for $key. Replacing it changes the live secret."
      if [[ "$SEND" != true ]] || confirm_typed "$key"; then
        set_key "$next" "$key" "$local_file"
        PLAN_LINES+=("REPLACE    $key (AWS already has a different value)")
        CHANGED=true
      else
        PLAN_LINES+=("keep       $key (existing AWS value kept)")
      fi
    elif $has_aws; then
      if [[ "$SEND" != true ]] \
        || confirm_default_yes "$key is blank in $(basename "$ENV_FILE") but AWS already has a value. Reuse the existing AWS value?"; then
        PLAN_LINES+=("reuse      $key (existing AWS value)")
      elif [[ "$kind" == required ]]; then
        die "$key is required. Fill ${key^^} in $ENV_FILE or choose to reuse the AWS value."
      else
        echo "Removing $key deletes it from flowform/$SCOPE/$suffix."
        if confirm_typed "$key"; then
          jq --arg k "$key" 'del(.[$k])' "$next" > "$next.tmp" && mv "$next.tmp" "$next"
          PLAN_LINES+=("REMOVE     $key")
          CHANGED=true
        else
          PLAN_LINES+=("reuse      $key (existing AWS value)")
        fi
      fi
    elif [[ "$kind" == required ]]; then
      die "$key is required but blank in both $ENV_FILE and AWS. Set ${key^^} in the env file."
    else
      PLAN_LINES+=("skip       $key (blank in both; optional)")
    fi
  done

  local extra
  while IFS= read -r extra; do
    [[ -n "$extra" ]] && PLAN_LINES+=("preserved  $extra (not managed by this script)")
  done < <(jq -r --arg managed "${required[*]} ${optional[*]}" \
    'keys[] | select(. as $k | ($managed | split(" ") | index($k)) | not)' "$current")
}

# ── Seeding ─────────────────────────────────────────────────────────────────

seed_secret() { # $1 = suffix ; $2 = required keys ; $3 = optional keys ; $4 = extra warning
  local suffix="$1" secret_id="flowform/$SCOPE/$1"
  echo
  echo "── $secret_id"
  fetch_current "$secret_id" "$TEMP_DIR/$suffix.current.json"
  plan_secret "$suffix" "$2" "${3:-}"

  echo "Plan:"
  printf '  %s\n' "${PLAN_LINES[@]}"
  if [[ "$CHANGED" != true ]]; then
    echo "No changes for $secret_id."
    return
  fi
  if [[ "$SEND" != true ]]; then
    echo "(dry run: --send asks before each add, replace and reuse, then before writing $secret_id)"
    return
  fi

  [[ -n "${4:-}" ]] && echo "note: $4"
  if ! confirm "Write these changes to $secret_id?"; then
    echo "Skipped $secret_id."
    return
  fi

  local version
  version="$(aws_sm put-secret-value --secret-id "$secret_id" \
    --secret-string "file://$TEMP_DIR/$suffix.new.json" --query VersionId --output text)" \
    || die "writing $secret_id failed; nothing else was changed."

  aws_sm get-secret-value --secret-id "$secret_id" --query SecretString --output text \
    > "$TEMP_DIR/$suffix.readback.json" \
    || die "$secret_id was written (version $version) but could not be read back to verify."
  if cmp -s <(jq -S -c . "$TEMP_DIR/$suffix.new.json") <(jq -S -c . "$TEMP_DIR/$suffix.readback.json"); then
    echo "Done: $secret_id (version $version) verified by read-back. The previous value remains as AWSPREVIOUS."
  else
    die "$secret_id read-back does not match what was written (version $version). Investigate before reseeding; the previous value remains as AWSPREVIOUS."
  fi
}

identity="$(aws sts get-caller-identity --query '[Account, Arn]' --output text)" \
  || die "no valid AWS session. Run 'aws login' and retry."
echo "Target: environment=$ENV_NAME scope=$SCOPE region=$AWS_REGION"
echo "Caller: $identity"

if [[ "$SEND" == true ]]; then
  confirm "Seed secrets for scope '$SCOPE' in this account?" || die "cancelled; nothing was written."
else
  echo "DRY RUN (no prompts, no changes) — re-run with --send to apply."
fi

seed_secret app-secrets "${APP_REQUIRED_KEYS[*]}" "${APP_OPTIONAL_KEYS[*]}"
seed_secret db-secrets "${DB_REQUIRED_KEYS[*]}" "" \
  "an initialized database keeps the role passwords it was created with; changing db-secrets alone does not rotate them, and the app would then fail to connect."
