#!/usr/bin/env bash
set -euo pipefail

# Assemble the dev secret files for docker-compose.dev.yml into a tmpfs
# directory. Two sources, by ownership:
#
#   1. Shared/persistent values -> AWS Secrets Manager (fetched via your
#      `aws login` session). Only what genuinely must persist or cannot
#      be generated lives there:
#        flowform/nonprod/app-secrets: app_secret_key, auth0_mgmt_secret
#      (dev and staging share the "nonprod" security scope — one KMS key
#      and one secret set for both; see infra/cdk security_stack.py)
#   2. Machine-local throwaways -> generated on this machine
#      (scripts/infra/generate-secrets.sh, invoked below when any file
#      is missing): the four local-Postgres passwords. They stay in
#      gitignored infra/docker/secrets/ so they survive reboots alongside
#      the Postgres volume they initialised (regenerating them requires a
#      DB volume reset), and are copied into the tmpfs dir here so
#      Compose reads everything from one FLOWFORM_SECRET_DIR.
#
# This mirrors the EC2 bootstrap flow (see the Secrets and Configuration
# Bootstrap section in
# infra/cdk/docs/implementation-sketch/caddy-ec2-implementation-notes.md);
# on EC2 the DB passwords come from the database stack/RDS instead.
#
# Usage:
#   scripts/infra/fetch-dev-secrets.sh
#   FLOWFORM_SECRET_DIR="$XDG_RUNTIME_DIR/flowform-secrets" \
#     docker compose -f infra/docker/docker-compose.dev.yml up -d
#
# (Export FLOWFORM_SECRET_DIR in your shell rc so compose always finds it.)
# tmpfs empties on reboot — just re-run this script.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/infra/docker"
ENV_NAME=dev

# Refuse to fall back to /tmp: on many systems (WSL2 included) it is real
# disk, which silently defeats the never-on-disk goal for fetched values.
if [[ -z "${XDG_RUNTIME_DIR:-}" ]]; then
  echo "error: XDG_RUNTIME_DIR is not set; refusing to write secrets to disk." >&2
  echo "       (expected a tmpfs like /run/user/\$UID)" >&2
  exit 1
fi
if ! findmnt -n -o FSTYPE --target "${XDG_RUNTIME_DIR}" 2>/dev/null | grep -q tmpfs; then
  echo "error: ${XDG_RUNTIME_DIR} is not tmpfs; refusing to write secrets to disk." >&2
  exit 1
fi

OUT_DIR="${FLOWFORM_SECRET_DIR:-${XDG_RUNTIME_DIR}/flowform-secrets}"
# Secrets Manager namespace — dev shares the nonprod security scope with
# staging; ENV_NAME still names the local files compose expects.
SCOPE_NAME=nonprod

command -v aws >/dev/null 2>&1 || { echo "error: aws CLI not found" >&2; exit 1; }

echo "==> Fetching flowform/${SCOPE_NAME}/app-secrets"
APP_JSON="$(aws secretsmanager get-secret-value \
  --secret-id "flowform/${SCOPE_NAME}/app-secrets" \
  --query SecretString --output text)"

DB_PASSWORD_NAMES=(DATABASE_CORE_APP_PASSWORD DATABASE_CORE_INIT_PASSWORD
  DATABASE_RESPONSE_APP_PASSWORD DATABASE_RESPONSE_INIT_PASSWORD)

for name in "${DB_PASSWORD_NAMES[@]}"; do
  if [[ ! -f "${DOCKER_DIR}/secrets/${name}.${ENV_NAME}.secret.txt" ]]; then
    echo "==> Missing local DB passwords; generating throwaways"
    bash "${SCRIPT_DIR}/generate-secrets.sh" "${ENV_NAME}" \
      --output-dir "${DOCKER_DIR}/secrets" >/dev/null
    break
  fi
done

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"
chmod 700 "${OUT_DIR}"
umask 177

write_key() { # $1=json blob  $2=json key  $3=file name
  python3 -c '
import json, sys
value = json.loads(sys.argv[1])[sys.argv[2]]
if not value:
    raise SystemExit(f"error: empty value for key {sys.argv[2]!r} — seed it first")
print(value, end="")
' "$1" "$2" > "${OUT_DIR}/$3.${ENV_NAME}.secret.txt"
}

write_key "${APP_JSON}" app_secret_key    FLOWFORM_APP_SECRET_KEY
write_key "${APP_JSON}" auth0_mgmt_secret FLOWFORM_AUTH0_MGMT_SECRET

# 644, not 600: the Postgres containers read these as the non-root
# postgres user during initdb. They're machine-local throwaways, and the
# 0700 tmpfs dir already blocks other host users.
for name in "${DB_PASSWORD_NAMES[@]}"; do
  install -m 644 "${DOCKER_DIR}/secrets/${name}.${ENV_NAME}.secret.txt" \
    "${OUT_DIR}/${name}.${ENV_NAME}.secret.txt"
done

echo "==> Wrote $(ls "${OUT_DIR}" | wc -l) secret files to ${OUT_DIR}"
echo "==> Run compose with: FLOWFORM_SECRET_DIR=${OUT_DIR}"
