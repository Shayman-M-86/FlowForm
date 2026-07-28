#!/usr/bin/env bash
#
# Replace the generated observability-secret placeholder with the real Grafana
# Cloud token. The token is read from a file (preferred) or the process
# environment and is passed to the AWS CLI through a mode-0600 temporary file,
# never as a command-line argument.

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
Usage: seed-observability-secret.sh [--environment staging|prod] [--apply]

Dry-run is the default. Supply the token with GRAFANA_CLOUD_TOKEN_FILE
(preferred) or GRAFANA_CLOUD_TOKEN. Use --apply to write a new secret version.
EOF
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
  dev|staging)
    SECURITY_SCOPE="nonprod"
    ;;
  prod)
    SECURITY_SCOPE="prod"
    ;;
  *)
    die "unsupported environment: ${ENVIRONMENT}"
    ;;
esac

command -v aws >/dev/null 2>&1 || die "required command is unavailable: aws"
command -v python3 >/dev/null 2>&1 || die "required command is unavailable: python3"

if [[ -n "${GRAFANA_CLOUD_TOKEN_FILE:-}" ]]; then
  [[ -f "${GRAFANA_CLOUD_TOKEN_FILE}" ]] \
    || die "GRAFANA_CLOUD_TOKEN_FILE does not name a readable file"
  GRAFANA_TOKEN="$(<"${GRAFANA_CLOUD_TOKEN_FILE}")"
else
  GRAFANA_TOKEN="${GRAFANA_CLOUD_TOKEN:-}"
fi
[[ -n "${GRAFANA_TOKEN}" ]] || die "Grafana Cloud token is empty"

CALLER_ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
[[ "${CALLER_ACCOUNT}" == "${EXPECTED_AWS_ACCOUNT_ID}" ]] \
  || die "AWS caller account ${CALLER_ACCOUNT} does not match ${EXPECTED_AWS_ACCOUNT_ID}"

SECRET_ID="flowform/${SECURITY_SCOPE}/observability-secrets"
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
printf '%s' "${GRAFANA_TOKEN}" | python3 -c \
  'import json, sys; json.dump({"grafana_cloud_token": sys.stdin.read()}, sys.stdout)' \
  >"${SECRET_FILE}"
unset GRAFANA_TOKEN

aws secretsmanager put-secret-value \
  --region "${AWS_REGION}" \
  --secret-id "${SECRET_ID}" \
  --secret-string "file://${SECRET_FILE}" \
  --query VersionId \
  --output text \
  >/dev/null

printf 'Added a new secret version to %s in %s.\n' "${SECRET_ID}" "${AWS_REGION}"
