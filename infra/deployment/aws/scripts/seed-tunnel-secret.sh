#!/usr/bin/env bash
#
# Replace the generated tunnel-secret placeholder with the real remotely managed
# Cloudflare Tunnel token used by the hybrid proxy's cloudflared connector. The
# token is read from a file (preferred) or the process environment and is passed
# to the AWS CLI through a mode-0600 temporary file, never as a command-line
# argument. Mirrors seed-observability-secret.sh.

set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-southeast-2}"
EXPECTED_AWS_ACCOUNT_ID="${EXPECTED_AWS_ACCOUNT_ID:-908123139858}"
ENVIRONMENT="staging"
APPLY=false
TEMP_DIR=""

cleanup() {
  if [[ -n "${TEMP_DIR}" && -d "${TEMP_DIR}" ]]; then
    rm -rf -- "${TEMP_DIR}"
  fi
}

trap cleanup EXIT

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: seed-tunnel-secret.sh [--environment staging|prod] [--apply]

Dry-run is the default. Supply the token with CLOUDFLARE_TUNNEL_TOKEN_FILE
(preferred) or CLOUDFLARE_TUNNEL_TOKEN. The file may contain either the token
alone or one CLOUDFLARE_TUNNEL_TOKEN=... dotenv assignment. Use --apply to
write a new secret version.
EOF
}

read_token_file() {
  local token_file="$1"
  local line
  local token_value
  local -a meaningful_lines=()

  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line%$'\r'}"
    [[ "${line}" =~ ^[[:space:]]*$ ]] && continue
    [[ "${line}" =~ ^[[:space:]]*# ]] && continue
    meaningful_lines+=("${line}")
  done <"${token_file}"

  [[ "${#meaningful_lines[@]}" -eq 1 ]] \
    || die "tunnel token file must contain one token or one CLOUDFLARE_TUNNEL_TOKEN assignment"

  token_value="${meaningful_lines[0]}"
  if [[ "${token_value}" == CLOUDFLARE_TUNNEL_TOKEN=* ]]; then
    token_value="${token_value#CLOUDFLARE_TUNNEL_TOKEN=}"
    if [[ "${token_value}" == \"*\" || "${token_value}" == \'*\' ]]; then
      token_value="${token_value:1:${#token_value}-2}"
    elif [[ "${token_value}" == \"* || "${token_value}" == \'* ]]; then
      die "tunnel token assignment has mismatched quotes"
    fi
  elif [[ "${token_value}" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
    die "tunnel token file contains an unexpected dotenv variable"
  fi
  printf '%s' "${token_value}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment)
      [[ $# -ge 2 ]] || die "--environment requires a value"
      ENVIRONMENT="$2"
      shift 2
      ;;
    --apply)
      APPLY=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

case "${ENVIRONMENT}" in
  dev|staging) SECURITY_SCOPE="nonprod" ;;
  prod) SECURITY_SCOPE="prod" ;;
  *) die "unsupported environment: ${ENVIRONMENT}" ;;
esac

command -v aws >/dev/null 2>&1 || die "required command is unavailable: aws"
command -v jq >/dev/null 2>&1 || die "required command is unavailable: jq"

if [[ -n "${CLOUDFLARE_TUNNEL_TOKEN_FILE:-}" ]]; then
  [[ -f "${CLOUDFLARE_TUNNEL_TOKEN_FILE}" ]] \
    || die "CLOUDFLARE_TUNNEL_TOKEN_FILE does not name a readable file"
  TUNNEL_TOKEN="$(read_token_file "${CLOUDFLARE_TUNNEL_TOKEN_FILE}")"
else
  TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-}"
fi
[[ -n "${TUNNEL_TOKEN}" ]] || die "Cloudflare Tunnel token is empty"
# Remotely managed tunnel tokens are a single base64 string.
[[ "${TUNNEL_TOKEN}" =~ ^[A-Za-z0-9+/=_-]+$ ]] \
  || die "Cloudflare Tunnel token contains unexpected characters (expected the base64 token from 'cloudflared tunnel token' or the dashboard)"

CALLER_ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
[[ "${CALLER_ACCOUNT}" == "${EXPECTED_AWS_ACCOUNT_ID}" ]] \
  || die "AWS caller account ${CALLER_ACCOUNT} does not match ${EXPECTED_AWS_ACCOUNT_ID}"

SECRET_ID="flowform/${SECURITY_SCOPE}/tunnel-secrets"
aws secretsmanager describe-secret \
  --region "${AWS_REGION}" \
  --secret-id "${SECRET_ID}" \
  >/dev/null

if [[ "${APPLY}" != true ]]; then
  printf 'DRY RUN: would add a new version to %s in %s.\n' "${SECRET_ID}" "${AWS_REGION}"
  printf 'Re-run with --apply to write it.\n'
  exit 0
fi

TEMP_DIR="$(mktemp -d)"
chmod 700 "${TEMP_DIR}"
SECRET_FILE="${TEMP_DIR}/secret.json"
umask 077
printf '%s' "${TUNNEL_TOKEN}" | jq -Rs '{cloudflare_tunnel_token: .}' >"${SECRET_FILE}"
unset TUNNEL_TOKEN

aws secretsmanager put-secret-value \
  --region "${AWS_REGION}" \
  --secret-id "${SECRET_ID}" \
  --secret-string "file://${SECRET_FILE}" \
  --query VersionId \
  --output text \
  >/dev/null

printf 'Added a new secret version to %s in %s.\n' "${SECRET_ID}" "${AWS_REGION}"
