#!/usr/bin/env bash
set -Eeuo pipefail

# Run terraform with the Auth0 values from the dev backend env exported as
# TF_VAR_* — so the rehearsal validates tokens against the same tenant your dev
# stack does, without those values being committed.
#
# Why sourced rather than defaulted in variables.tf: the rehearsal is only
# useful if it accepts the tokens your Studio front end already issues, which
# means issuer + audience + client id must match dev exactly. Duplicating them
# into a committed default guarantees they drift the first time either side
# changes tenant; reading the one file dev already reads means they cannot.
#
# infra/env/dev/.backend.env is gitignored (.gitignore: env/), so nothing here
# lands in git. These are non-secret identifiers — domains, audience, client id.
#
# The Auth0 mgmt CLIENT SECRET *is* a real secret, and this wrapper now fetches
# it too: from AWS Secrets Manager (flowform/nonprod/app-secrets → auth0_mgmt_secret,
# the same source scripts/secrets/fetch-dev-secrets.sh reads for the dev stack)
# using your `aws login` session, exported as TF_VAR_auth0_mgmt_secret. The
# rehearsal seeds that real value into its LocalStack app-secrets instead of a
# throwaway, so the Management API works and startup validation is on — see
# FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP in variables.tf. Set AUTH0_MGMT_SECRET
# in the environment to override the AWS fetch (e.g. no login available).
#
# This wrapper ALSO exports the Grafana Cloud token for the proxy-box Alloy agent
# as TF_VAR_grafana_cloud_token. Unlike the Auth0 identifiers this is a real
# secret, so it is read from its own gitignored file (infra/env/dev/.grafana.env,
# GRAFANA_CLOUD_TOKEN=...) or the GRAFANA_CLOUD_TOKEN env var. It is required:
# terraform's grafana_cloud_token variable has no default, so a missing token
# fails here rather than silently shipping logs to nowhere.
#
# Usage:
#   with-dev-auth0-env.sh plan
#   with-dev-auth0-env.sh apply -auto-approve
#
# Override the source files with DEV_BACKEND_ENV=/path/to/.backend.env and
# GRAFANA_ENV=/path/to/.grafana.env. GRAFANA_CLOUD_TOKEN in the environment wins
# over the file.
#
# SSH PREFLIGHT: the bpg/proxmox provider uploads cloud-init snippets over SSH to
# the Proxmox node as root, using ssh-agent only (it ignores ~/.ssh/config). A
# terminal without the PVE key loaded fails deep inside `apply` with an opaque
# "unable to authenticate user root" error. So before running terraform this
# wrapper ensures an agent is running, loads the PVE key into it, and verifies
# root@<node> is reachable — turning that late failure into an early, clear one.
#   PVE_SSH_KEY   private key the node's root authorises (default ~/.ssh/proxmox_codex)
#   PVE_SSH_HOST  node host to check (default: parsed from proxmox_endpoint in tfvars)
#   SKIP_SSH_PREFLIGHT=1  bypass entirely (e.g. non-root ssh user, jump host)

log() { printf '[with-dev-auth0-env] %s\n' "$*" >&2; }
die() { printf '[with-dev-auth0-env] ERROR: %s\n' "$*" >&2; exit 1; }

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="${HERE}/../terraform"
REPO_ROOT="$(cd -- "${HERE}/../../../.." && pwd)"
DEV_BACKEND_ENV="${DEV_BACKEND_ENV:-${REPO_ROOT}/infra/env/dev/.backend.env}"
GRAFANA_ENV="${GRAFANA_ENV:-${REPO_ROOT}/infra/env/dev/.grafana.env}"

[[ -f "${DEV_BACKEND_ENV}" ]] || die "dev backend env not found: ${DEV_BACKEND_ENV}
  This file is gitignored and machine-local. Create it as you would for the dev
  stack, or point at another with DEV_BACKEND_ENV=."

# Read a single KEY= line out of a compose-style env_file without sourcing it:
# it is a compose env_file, not a shell script — unquoted values with spaces or a
# stray `$` would execute or mangle under `source`. Prints the cleaned value.
read_env_value() {
  local key="$1" file="$2" line value
  line="$(grep -E "^${key}=" "${file}" | tail -n1 || true)"
  [[ -n "${line}" ]] || return 1
  value="${line#*=}"
  value="${value%$'\r'}"                            # tolerate CRLF
  value="${value#[\"\']}"; value="${value%[\"\']}"  # strip matching quotes
  [[ -n "${value}" ]] || return 1
  printf '%s' "${value}"
}

# dev env var  ->  terraform variable
declare -A WANTED=(
  [FLOWFORM_AUTH0_DOMAIN]=auth0_domain
  [FLOWFORM_AUTH0_AUDIENCE]=auth0_audience
  [FLOWFORM_AUTH0_CLIENT_ID]=auth0_client_id
  [FLOWFORM_AUTH0_MGMT_DOMAIN]=auth0_mgmt_domain
  [FLOWFORM_AUTH0_MGMT_ID]=auth0_mgmt_id
)

for key in "${!WANTED[@]}"; do
  value="$(read_env_value "${key}" "${DEV_BACKEND_ENV}")" \
    || die "${key} not set (or empty) in ${DEV_BACKEND_ENV}"
  export "TF_VAR_${WANTED[$key]}=${value}"
done

log "Auth0 vars sourced from ${DEV_BACKEND_ENV#"${REPO_ROOT}/"}"
log "issuer: ${TF_VAR_auth0_domain} | mgmt: ${TF_VAR_auth0_mgmt_domain}"

# Grafana Cloud token: env var wins, else the gitignored .grafana.env file.
# Required — terraform's grafana_cloud_token has no default, so fail fast here.
grafana_token="${GRAFANA_CLOUD_TOKEN:-}"
grafana_source="GRAFANA_CLOUD_TOKEN env var"
if [[ -z "${grafana_token}" ]]; then
  [[ -f "${GRAFANA_ENV}" ]] || die "Grafana token not found.
  Set GRAFANA_CLOUD_TOKEN in the environment, or create the gitignored file
  ${GRAFANA_ENV} with a line: GRAFANA_CLOUD_TOKEN=glc_...
  Override the path with GRAFANA_ENV=/path/to/.grafana.env."
  grafana_token="$(read_env_value GRAFANA_CLOUD_TOKEN "${GRAFANA_ENV}")" \
    || die "GRAFANA_CLOUD_TOKEN not set (or empty) in ${GRAFANA_ENV}"
  grafana_source="${GRAFANA_ENV#"${REPO_ROOT}/"}"
fi
export TF_VAR_grafana_cloud_token="${grafana_token}"
log "Grafana Cloud token sourced from ${grafana_source}"

# Auth0 management client secret: a real secret. The AUTH0_MGMT_SECRET env var
# wins (e.g. no AWS login available); otherwise fetch it from AWS Secrets Manager
# — the same secret id and json key the dev stack's fetch-dev-secrets.sh reads,
# so rehearsal and dev share one management secret. Required: terraform's
# auth0_mgmt_secret variable has no default, so a missing value fails fast here.
mgmt_secret="${AUTH0_MGMT_SECRET:-}"
mgmt_source="AUTH0_MGMT_SECRET env var"
if [[ -z "${mgmt_secret}" ]]; then
  command -v aws >/dev/null 2>&1 || die "aws CLI not found.
  Install and 'aws login', or set AUTH0_MGMT_SECRET in the environment to
  supply the Auth0 management client secret without an AWS fetch."
  mgmt_app_json="$(aws secretsmanager get-secret-value \
    --secret-id "flowform/nonprod/app-secrets" \
    --query SecretString --output text 2>/dev/null)" \
    || die "failed to read flowform/nonprod/app-secrets from AWS Secrets Manager.
  Run 'aws login' first, or set AUTH0_MGMT_SECRET in the environment."
  mgmt_secret="$(printf '%s' "${mgmt_app_json}" | python3 -c \
    'import json,sys; print(json.loads(sys.stdin.read()).get("auth0_mgmt_secret",""), end="")')" \
    || die "could not parse auth0_mgmt_secret out of flowform/nonprod/app-secrets."
  [[ -n "${mgmt_secret}" ]] \
    || die "auth0_mgmt_secret is empty in flowform/nonprod/app-secrets — seed it first."
  mgmt_source="AWS Secrets Manager (flowform/nonprod/app-secrets)"
fi
export TF_VAR_auth0_mgmt_secret="${mgmt_secret}"
log "Auth0 management secret sourced from ${mgmt_source}"

# --- SSH preflight: prime ssh-agent so the provider can reach the PVE node -----
ssh_preflight() {
  [[ "${SKIP_SSH_PREFLIGHT:-0}" == "1" ]] && { log "SSH preflight skipped (SKIP_SSH_PREFLIGHT=1)"; return; }

  local key="${PVE_SSH_KEY:-${HOME}/.ssh/proxmox_codex}"

  # Node host: explicit override, else the host[:port] parsed out of
  # proxmox_endpoint (https://HOST:8006/api2/json) in terraform.tfvars.
  local host="${PVE_SSH_HOST:-}"
  if [[ -z "${host}" ]]; then
    local endpoint
    # terraform.tfvars is HCL (proxmox_endpoint = "https://host:port/path"),
    # not a compose env_file, so parse it directly: tolerate spaces around = and
    # the surrounding quotes rather than reusing read_env_value.
    endpoint="$(sed -nE 's/^[[:space:]]*proxmox_endpoint[[:space:]]*=[[:space:]]*"?([^"]+)"?.*/\1/p' \
      "${TERRAFORM_DIR}/terraform.tfvars" 2>/dev/null | tail -n1)"
    # strip scheme, then any :port and trailing path.
    host="${endpoint#*://}"
    host="${host%%[:/]*}"
  fi
  [[ -n "${host}" ]] || die "cannot determine the Proxmox node host.
  Set PVE_SSH_HOST=<node>, or ensure proxmox_endpoint is set in
  ${TERRAFORM_DIR#"${REPO_ROOT}/"}/terraform.tfvars. Or SKIP_SSH_PREFLIGHT=1."

  # An agent must be reachable for the provider's agent=true to work. If this
  # shell has none, start one scoped to this process (and its terraform child).
  if [[ -z "${SSH_AUTH_SOCK:-}" ]] || ! ssh-add -l >/dev/null 2>&1; then
    if [[ -z "${SSH_AUTH_SOCK:-}" ]]; then
      log "no ssh-agent in this shell — starting one for this run"
      eval "$(ssh-agent -s)" >/dev/null || die "failed to start ssh-agent"
    fi
  fi

  # Load the PVE key unless the agent already carries it. Compare by public key
  # so a key added under a different path/comment still counts as present.
  if [[ -r "${key}" ]]; then
    local want
    want="$(ssh-keygen -y -f "${key}" 2>/dev/null | awk '{print $1" "$2}')"
    if [[ -n "${want}" ]] && ssh-add -L 2>/dev/null | awk '{print $1" "$2}' | grep -qxF "${want}"; then
      log "PVE key already loaded in agent"
    else
      ssh-add "${key}" >/dev/null 2>&1 || die "ssh-add failed for ${key}.
  Set PVE_SSH_KEY to the private key root@${host} authorises, or SKIP_SSH_PREFLIGHT=1."
      log "loaded PVE key ${key/#${HOME}/\~} into agent"
    fi
  elif ! ssh-add -l >/dev/null 2>&1; then
    die "PVE key not found at ${key} and the agent has no identities.
  Set PVE_SSH_KEY=/path/to/key (root@${host} must authorise it), or SKIP_SSH_PREFLIGHT=1."
  fi

  # Fail fast if root still cannot get in — clearer here than inside `apply`.
  if ! ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new \
        "root@${host}" true >/dev/null 2>&1; then
    die "root@${host} is not reachable over SSH with the loaded key(s).
  Verify: ssh -i ${key} root@${host} true
  The key's PUBLIC half must be in /root/.ssh/authorized_keys on the node.
  (~/.ssh/config is ignored by the provider — the key must be in the agent.)
  Bypass this check with SKIP_SSH_PREFLIGHT=1."
  fi
  log "SSH preflight OK — root@${host} reachable"
}
ssh_preflight

exec terraform -chdir="${TERRAFORM_DIR}" "$@"
