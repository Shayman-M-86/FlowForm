#!/usr/bin/env bash
# Shared secret-bundle operations for `rehearsal sync` and `rehearsal rotate`.
# This file is sourced after rehearsal-common.sh. Persistent managed values are
# generated and stored on the PVE host; deploy-time values use private local and
# remote staging directories and are sent as file/stdin content, never argv.

if [[ -n "${_REHEARSAL_SECRETS_SOURCED:-}" ]]; then
  return
fi
_REHEARSAL_SECRETS_SOURCED=1

FLOWFORM_SCOPE="${FLOWFORM_SCOPE:-nonprod}"
AWS_REGION="${AWS_REGION:-ap-southeast-2}"
BUNDLE_DIR="${REHEARSAL_SECRET_BUNDLE_DIR:-/var/lib/flowform/rehearsal-secrets/${FLOWFORM_SCOPE}}"
FIXTURES_SSH_IP="${FIXTURES_SSH_IP:-$(rehearsal_ip fixtures)}"
LS_SYNC_SCRIPT="${LS_SYNC_SCRIPT:-/opt/flowform/localstack/sync-secrets-into-localstack.sh}"

_SECRETS_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
_SECRETS_REPO_ROOT="$(cd -- "${_SECRETS_LIB_DIR}/../../../../.." && pwd)"
AUTH0_MGMT_SECRET_FILE="${AUTH0_MGMT_SECRET_FILE:-}"
GRAFANA_CLOUD_TOKEN_FILE="${GRAFANA_CLOUD_TOKEN_FILE:-}"
GRAFANA_ENV="${GRAFANA_ENV:-${_SECRETS_REPO_ROOT}/infra/env/dev/.grafana.env}"
SSH_RELAY_MAX_ATTEMPTS="${SYNC_RELAY_MAX_ATTEMPTS:-60}"
SSH_RELAY_RETRY_DELAY_SECONDS="${SYNC_RELAY_RETRY_DELAY_SECONDS:-2}"
LOCALSTACK_HEALTH_MAX_ATTEMPTS="${LOCALSTACK_HEALTH_MAX_ATTEMPTS:-90}"
LOCALSTACK_HEALTH_RETRY_DELAY_SECONDS="${LOCALSTACK_HEALTH_RETRY_DELAY_SECONDS:-2}"

WORK_DIR=""
REMOTE_STAGE=""
ROTATION_BACKUP_DIR=""

secrets_preflight() {
  rehearsal_preflight
  rehearsal_preflight_pve_tools
  command -v tar >/dev/null 2>&1 || die "tar not found on this box"
}

fixtures_ssh() { guest_ssh "${FIXTURES_SSH_IP}" "$@"; }

secrets_wait_for_localstack() {
  local attempt
  fixtures_ssh "command -v curl >/dev/null 2>&1" \
    || die "curl is unavailable in fixtures VM 230; inspect the VM image/bootstrap, then rerun 'rehearsal sync'"

  for ((attempt = 1; attempt <= LOCALSTACK_HEALTH_MAX_ATTEMPTS; attempt++)); do
    if fixtures_ssh \
      "curl -fsS --max-time 5 http://127.0.0.1:4566/_localstack/health >/dev/null 2>&1"; then
      log "LocalStack healthy in fixtures VM 230"
      return 0
    fi
    if ((attempt == 1 || attempt % 10 == 0)); then
      log "waiting for LocalStack health in VM 230 (${attempt}/${LOCALSTACK_HEALTH_MAX_ATTEMPTS})"
    fi
    sleep "${LOCALSTACK_HEALTH_RETRY_DELAY_SECONDS}"
  done

  die "LocalStack did not become healthy in VM 230 after ${LOCALSTACK_HEALTH_MAX_ATTEMPTS} attempts. Run 'rehearsal logs fixtures -c flowform-localstack --raw -n 100' and 'rehearsal logs fixtures --system --raw -n 100', resolve the startup error, then rerun 'rehearsal sync'."
}

secrets_make_work_dir() {
  WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/flowform-secret-sync.XXXXXX")" \
    || die "could not create a local staging directory"
  chmod 0700 "${WORK_DIR}"
}

secrets_cleanup_resources() {
  if [[ -n "${REMOTE_STAGE}" ]]; then
    pve_ssh "rm -rf -- '${REMOTE_STAGE}'" >/dev/null 2>&1 || true
    REMOTE_STAGE=""
  fi
  if [[ -n "${WORK_DIR}" && -d "${WORK_DIR}" ]]; then
    rm -rf -- "${WORK_DIR}"
    WORK_DIR=""
  fi
  rehearsal_bridge_down
}

secrets_ensure_bundle() {
  log "ensuring persistent secret bundle at ${PVE_USER}@${PVE_HOST}:${BUNDLE_DIR}"
  pve_ssh "FLOWFORM_SCOPE='${FLOWFORM_SCOPE}' BUNDLE_DIR='${BUNDLE_DIR}' bash -s" <<'REMOTE' \
    || return 1
set -Eeuo pipefail
umask 077
install -d -m 0700 "$(dirname "${BUNDLE_DIR}")"
install -d -m 0700 "${BUNDLE_DIR}"

gen_hex() { openssl rand -hex "$1"; }
ensure_file() {
  local path="$1"; shift
  [[ -s "${path}" ]] || (umask 077; "$@" > "${path}")
  chmod 0600 "${path}"
}

ensure_file "${BUNDLE_DIR}/app_secret_key"           gen_hex 32
ensure_file "${BUNDLE_DIR}/db_core_app_password"     gen_hex 16
ensure_file "${BUNDLE_DIR}/db_response_app_password" gen_hex 16

if [[ ! -s "${BUNDLE_DIR}/linkage_history.json" ]]; then
  python3 - "${BUNDLE_DIR}/linkage_history.json" <<'PY'
import base64, json, os, secrets, sys, uuid
path = sys.argv[1]
with open(path, "x", encoding="utf-8") as handle:
    json.dump([{
        "version": 1,
        "secret_b64": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
        "client_request_token": str(uuid.uuid4()),
    }], handle, separators=(",", ":"))
    handle.write("\n")
os.chmod(path, 0o600)
PY
fi
python3 - "${BUNDLE_DIR}/linkage_history.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    history = json.load(handle)
if not isinstance(history, list) or not history:
    raise SystemExit("linkage history must be a non-empty array")
for item in history:
    if not isinstance(item.get("version"), int) or item["version"] < 1:
        raise SystemExit("invalid linkage version")
    if not item.get("secret_b64") or not item.get("client_request_token"):
        raise SystemExit("incomplete linkage history entry")
PY
chmod 0600 "${BUNDLE_DIR}/linkage_history.json"
chmod 0700 "${BUNDLE_DIR}"
echo bundle-ok
REMOTE
}

_resolve_external_secret() {
  local out="$1" file="$2" env_name="$3" label="$4"
  if [[ -n "${file}" ]]; then
    (umask 077
      [[ -r "${file}" ]] || die "${label}: *_FILE path not readable: ${file}"
      tr -d '\r\n' < "${file}" > "${out}")
  elif [[ -n "${!env_name:-}" ]]; then
    (umask 077
      printf '%s' "${!env_name}" | tr -d '\r\n' > "${out}"
    )
  else
    return 3
  fi
  [[ -s "${out}" ]] || die "${label}: the selected file/environment source is empty; correct it and rerun 'rehearsal sync'"
  chmod 0600 "${out}"
}

_read_env_value() {
  local key="$1" file="$2" line value
  line="$(grep -E "^${key}=" "${file}" | tail -n1 || true)"
  [[ -n "${line}" ]] || return 1
  value="${line#*=}"
  value="${value%$'\r'}"
  value="${value#[\"\']}"; value="${value%[\"\']}"
  [[ -n "${value}" ]] || return 1
  printf '%s' "${value}"
}

_aws_error_is_login_failure() {
  local message="${1,,}"
  [[ "${message}" == *"session has expired"* \
    || "${message}" == *"please reauthenticate using 'aws login'"* \
    || "${message}" == *"unable to locate credentials"* \
    || "${message}" == *"expiredtoken"* \
    || "${message}" == *"token has expired"* \
    || "${message}" == *"invalidclienttokenid"* \
    || "${message}" == *"unrecognizedclientexception"* \
    || "${message}" == *"cached sso token"*"expired"* ]]
}

_aws_resolve_login_profile() { # target profile -> writable base/source profile
  local current="$1" source seen=":"
  while :; do
    [[ "${seen}" != *":${current}:"* ]] \
      || die "AWS profile source_profile cycle detected while resolving ${1}"
    seen+="${current}:"
    source="$(aws configure get source_profile --profile "${current}" 2>/dev/null || true)"
    [[ -n "${source}" ]] || break
    current="${source}"
  done
  printf '%s' "${current}"
}

_ensure_aws_login_session() {
  export AWS_PROFILE="${AWS_PROFILE:-flowform-dev}"
  local check_output answer login_profile
  if check_output="$(aws sts get-caller-identity --profile "${AWS_PROFILE}" --output json --no-cli-pager 2>&1)"; then
    log "AWS session valid for profile ${AWS_PROFILE}"
    return 0
  fi

  if ! _aws_error_is_login_failure "${check_output}"; then
    die "AWS identity check failed for profile ${AWS_PROFILE}, but not because the login is expired/missing; refusing to run aws login automatically. AWS CLI said: ${check_output}"
  fi

  if [[ ! -t 0 || ! -t 1 ]]; then
    login_profile="$(_aws_resolve_login_profile "${AWS_PROFILE}")"
    die "AWS profile ${AWS_PROFILE} is confirmed logged out/expired. Its login-capable source profile is ${login_profile}; run 'aws login --profile ${login_profile}', then rerun the command."
  fi

  login_profile="$(_aws_resolve_login_profile "${AWS_PROFILE}")"
  if [[ "${login_profile}" != "${AWS_PROFILE}" ]]; then
    log "AWS profile ${AWS_PROFILE} assumes a role through source profile ${login_profile}"
  fi
  rehearsal_prompt \
    "AWS session for ${AWS_PROFILE} is logged out or expired; log into source profile ${login_profile} now? [y/N]"
  IFS= read -r answer
  case "${answer}" in
    y|Y|yes|YES|Yes) ;;
    *) die "AWS login declined; no Secrets Manager request was attempted" ;;
  esac

  aws login --profile "${login_profile}" \
    || die "aws login failed for source profile ${login_profile}; resolve the CLI/browser error and rerun the command"
  aws sts get-caller-identity --profile "${AWS_PROFILE}" --output json --no-cli-pager >/dev/null 2>&1 \
    || die "aws login returned success, but profile ${AWS_PROFILE} still has no valid STS session"
  log "AWS login completed for ${login_profile}; AssumeRole profile ${AWS_PROFILE} is valid"
}

secrets_resolve_external() {
  local out app_json token
  out="${WORK_DIR}/auth0_mgmt_secret"
  if _resolve_external_secret "${out}" "${AUTH0_MGMT_SECRET_FILE}" AUTH0_MGMT_SECRET "Auth0 management secret"; then
    log "Auth0 management secret resolved from ${AUTH0_MGMT_SECRET_FILE:+file}${AUTH0_MGMT_SECRET_FILE:-environment}"
  else
    command -v aws >/dev/null 2>&1 \
      || die "Auth0 management secret is unavailable. Set AUTH0_MGMT_SECRET_FILE, export AUTH0_MGMT_SECRET, or install the AWS CLI and run 'aws login'; then rerun 'rehearsal sync'"
    _ensure_aws_login_session
    local aws_error_file="${WORK_DIR}/aws-secretsmanager-error"
    if ! app_json="$(aws secretsmanager get-secret-value \
      --secret-id flowform/nonprod/app-secrets \
      --profile "${AWS_PROFILE}" --query SecretString --output text --no-cli-pager \
      2>"${aws_error_file}")"; then
      die "AWS session is valid, but reading flowform/nonprod/app-secrets failed. This is not treated as a login problem; verify the secret name, region, and profile permissions. AWS CLI said: $(tail -n 5 "${aws_error_file}")"
    fi
    (umask 077
      printf '%s' "${app_json}" | python3 -c \
        'import json,sys; sys.stdout.write(json.loads(sys.stdin.read()).get("auth0_mgmt_secret", ""))' > "${out}")
    [[ -s "${out}" ]] || die "auth0_mgmt_secret is missing or empty in flowform/nonprod/app-secrets; seed/fix that AWS secret or provide AUTH0_MGMT_SECRET_FILE, then rerun 'rehearsal sync'"
    chmod 0600 "${out}"
    log "Auth0 management secret resolved from AWS Secrets Manager"
  fi

  out="${WORK_DIR}/grafana_cloud_token"
  if _resolve_external_secret "${out}" "${GRAFANA_CLOUD_TOKEN_FILE}" GRAFANA_CLOUD_TOKEN "Grafana Cloud token"; then
    log "Grafana Cloud token resolved from ${GRAFANA_CLOUD_TOKEN_FILE:+file}${GRAFANA_CLOUD_TOKEN_FILE:-environment}"
  elif [[ -f "${GRAFANA_ENV}" ]] && token="$(_read_env_value GRAFANA_CLOUD_TOKEN "${GRAFANA_ENV}")"; then
    (umask 077; printf '%s' "${token}" > "${out}")
    chmod 0600 "${out}"
    log "Grafana Cloud token resolved from ${GRAFANA_ENV#"${_SECRETS_REPO_ROOT}/"}"
  else
    die "Grafana Cloud token is unavailable. Set GRAFANA_CLOUD_TOKEN_FILE, export GRAFANA_CLOUD_TOKEN, or add a non-empty GRAFANA_CLOUD_TOKEN entry to ${GRAFANA_ENV}; then rerun 'rehearsal sync'"
  fi
}

secrets_preflight_build_inputs() {
  secrets_preflight
  secrets_make_work_dir
  secrets_resolve_external
  secrets_cleanup_resources
  log "required external secret inputs are available"
}

secrets_prepare_bridge() {
  pve_ssh "ip link show '${BRIDGE}'" >/dev/null \
    || die "cannot access ${BRIDGE} on ${PVE_USER}@${PVE_HOST}"
  rehearsal_bridge_up
  rehearsal_wait_for_guest fixtures "${SSH_RELAY_MAX_ATTEMPTS}" "${SSH_RELAY_RETRY_DELAY_SECONDS}" \
    || die "fixtures VM (${GUEST_USER}@${FIXTURES_SSH_IP}) is unreachable"
  secrets_wait_for_localstack
}

secrets_validate_inputs() {
  local file
  for file in auth0_mgmt_secret grafana_cloud_token; do
    [[ -s "${WORK_DIR}/${file}" ]] || case "${file}" in
      auth0_mgmt_secret)
        die "Auth0 management secret staging file is missing/empty. Set AUTH0_MGMT_SECRET_FILE, AUTH0_MGMT_SECRET, or run 'aws login', then rerun 'rehearsal sync'"
        ;;
      grafana_cloud_token)
        die "Grafana token staging file is missing/empty. Set GRAFANA_CLOUD_TOKEN_FILE/GRAFANA_CLOUD_TOKEN or fix ${GRAFANA_ENV}, then rerun 'rehearsal sync'"
        ;;
    esac
  done

  pve_ssh "BUNDLE_DIR='${BUNDLE_DIR}' bash -s" <<'REMOTE' || return 1
set -Eeuo pipefail
for file in app_secret_key db_core_app_password db_response_app_password linkage_history.json; do
  [[ -s "${BUNDLE_DIR}/${file}" ]] || {
    printf 'required bundle secret is missing or empty: %s/%s\n' "${BUNDLE_DIR}" "${file}" >&2
    printf 'rerun rehearsal sync to regenerate missing create-once values; if it persists, inspect PVE bundle ownership/mode (root:root, 0700 dir, 0600 files)\n' >&2
    exit 1
  }
done

python3 - "${BUNDLE_DIR}/linkage_history.json" <<'PY' || {
import base64, binascii, json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    history = json.load(handle)
if not isinstance(history, list) or not history:
    raise ValueError("history must be a non-empty array")
versions = []
for item in history:
    version = item.get("version")
    if not isinstance(version, int) or version < 1:
        raise ValueError("every version must be a positive integer")
    if not isinstance(item.get("client_request_token"), str) or not item["client_request_token"]:
        raise ValueError("every entry needs a client_request_token")
    versions.append(version)
if len(versions) != len(set(versions)):
    raise ValueError("linkage versions must be unique")
try:
    current = base64.b64decode(history[-1]["secret_b64"], validate=True)
except (KeyError, TypeError, binascii.Error) as exc:
    raise ValueError("current secret_b64 is invalid") from exc
if len(current) < 32:
    raise ValueError("current linkage secret decodes to fewer than 32 bytes")
PY
  printf 'linkage history is invalid; inspect %s/linkage_history.json and any protected .rotation.* backup, then rerun rehearsal sync\n' "${BUNDLE_DIR}" >&2
  exit 1
}
REMOTE
}

secrets_stream_archive() {
  secrets_validate_inputs || return 1
  REMOTE_STAGE="$(pve_ssh 'mktemp -d /dev/shm/flowform-sync.XXXXXX')" \
    || return 1
  [[ "${REMOTE_STAGE}" == /dev/shm/flowform-sync.* ]] || return 1
  pve_ssh "chmod 0700 '${REMOTE_STAGE}'" || return 1

  pve_ssh "umask 077; cat > '${REMOTE_STAGE}/auth0_mgmt_secret'" < "${WORK_DIR}/auth0_mgmt_secret" || return 1
  pve_ssh "umask 077; cat > '${REMOTE_STAGE}/grafana_cloud_token'" < "${WORK_DIR}/grafana_cloud_token" || return 1
  pve_ssh "chmod 0600 '${REMOTE_STAGE}/auth0_mgmt_secret' '${REMOTE_STAGE}/grafana_cloud_token'" || return 1

  log "assembling allow-listed secret archive on the PVE host and streaming it into VM 230"
  local status=0
  if pve_ssh "FLOWFORM_SCOPE='${FLOWFORM_SCOPE}' BUNDLE_DIR='${BUNDLE_DIR}' STAGE='${REMOTE_STAGE}' bash -s" <<'REMOTE' \
    | fixtures_ssh "sudo FLOWFORM_SCOPE='${FLOWFORM_SCOPE}' AWS_REGION='${AWS_REGION}' ${LS_SYNC_SCRIPT}"; then
set -Eeuo pipefail
umask 077
out="${STAGE}/archive"
install -d -m 0700 "${out}"
python3 - "${BUNDLE_DIR}" "${STAGE}" "${out}" "${FLOWFORM_SCOPE}" <<'PY'
import json, os, pathlib, sys
bundle = pathlib.Path(sys.argv[1])
stage = pathlib.Path(sys.argv[2])
out = pathlib.Path(sys.argv[3])
scope = sys.argv[4]
def read(path):
    return path.read_text(encoding="utf-8").rstrip("\r\n")
history = json.loads(read(bundle / "linkage_history.json"))
current = history[-1]
payloads = {
    "app-secrets.json": {"app_secret_key": read(bundle / "app_secret_key"), "auth0_mgmt_secret": read(stage / "auth0_mgmt_secret")},
    "db-secrets.json": {"db_core_app_password": read(bundle / "db_core_app_password"), "db_response_app_password": read(bundle / "db_response_app_password")},
    "linkage-secret.json": {"version": current["version"], "secret_b64": current["secret_b64"]},
    "observability-secrets.json": {"grafana_cloud_token": read(stage / "grafana_cloud_token")},
    "meta.json": {"scope": scope},
}
for name, value in payloads.items():
    path = out / name
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
token = out / "linkage-client-request-token"
token.write_text(current["client_request_token"], encoding="utf-8")
os.chmod(token, 0o600)
PY
chmod 0600 "${out}"/*
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='@0' \
  -C "${out}" -cf - \
  app-secrets.json db-secrets.json linkage-secret.json observability-secrets.json \
  linkage-client-request-token meta.json
REMOTE
    status=0
  else
    status=$?
  fi

  pve_ssh "rm -rf -- '${REMOTE_STAGE}'" >/dev/null 2>&1 || true
  REMOTE_STAGE=""
  return "${status}"
}

secrets_begin_rotation() { # app|database|linkage
  local target="$1"
  ROTATION_BACKUP_DIR="$(pve_ssh "BUNDLE_DIR='${BUNDLE_DIR}' TARGET='${target}' bash -s" <<'REMOTE'
set -Eeuo pipefail
umask 077
backup="$(mktemp -d "${BUNDLE_DIR}/.rotation.XXXXXX")"
chmod 0700 "${backup}"
new_file() { mktemp "${BUNDLE_DIR}/.new.XXXXXX"; }
case "${TARGET}" in
  app)
    cp -p "${BUNDLE_DIR}/app_secret_key" "${backup}/"
    tmp="$(new_file)"; openssl rand -hex 32 > "${tmp}"; chmod 0600 "${tmp}"
    mv -f "${tmp}" "${BUNDLE_DIR}/app_secret_key"
    ;;
  database)
    cp -p "${BUNDLE_DIR}/db_core_app_password" "${BUNDLE_DIR}/db_response_app_password" "${backup}/"
    for name in db_core_app_password db_response_app_password; do
      tmp="$(new_file)"; openssl rand -hex 16 > "${tmp}"; chmod 0600 "${tmp}"
      mv -f "${tmp}" "${BUNDLE_DIR}/${name}"
    done
    ;;
  linkage)
    cp -p "${BUNDLE_DIR}/linkage_history.json" "${backup}/"
    tmp="$(new_file)"
    python3 - "${BUNDLE_DIR}/linkage_history.json" "${tmp}" <<'PY'
import base64, json, secrets, sys, uuid
with open(sys.argv[1], encoding="utf-8") as handle:
    history = json.load(handle)
history.append({
    "version": history[-1]["version"] + 1,
    "secret_b64": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
    "client_request_token": str(uuid.uuid4()),
})
with open(sys.argv[2], "w", encoding="utf-8") as handle:
    json.dump(history, handle, separators=(",", ":"))
    handle.write("\n")
PY
    chmod 0600 "${tmp}"; mv -f "${tmp}" "${BUNDLE_DIR}/linkage_history.json"
    ;;
  *) exit 2 ;;
esac
printf '%s\n' "${backup}"
REMOTE
)" || return 1
  [[ "${ROTATION_BACKUP_DIR}" == "${BUNDLE_DIR}/.rotation."* ]]
}

secrets_restore_rotation() {
  local target="$1"
  [[ -n "${ROTATION_BACKUP_DIR}" ]] || return 0
  pve_ssh "BUNDLE_DIR='${BUNDLE_DIR}' BACKUP='${ROTATION_BACKUP_DIR}' TARGET='${target}' bash -s" <<'REMOTE'
set -Eeuo pipefail
case "${TARGET}" in
  app)      install -m 0600 "${BACKUP}/app_secret_key" "${BUNDLE_DIR}/app_secret_key" ;;
  database) install -m 0600 "${BACKUP}/db_core_app_password" "${BUNDLE_DIR}/db_core_app_password"
            install -m 0600 "${BACKUP}/db_response_app_password" "${BUNDLE_DIR}/db_response_app_password" ;;
  linkage)  install -m 0600 "${BACKUP}/linkage_history.json" "${BUNDLE_DIR}/linkage_history.json" ;;
  *) exit 2 ;;
esac
REMOTE
}

secrets_finish_rotation() {
  [[ -n "${ROTATION_BACKUP_DIR}" ]] || return 0
  pve_ssh "rm -rf -- '${ROTATION_BACKUP_DIR}'"
  ROTATION_BACKUP_DIR=""
}
