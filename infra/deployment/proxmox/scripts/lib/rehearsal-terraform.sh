#!/usr/bin/env bash
# Shared Terraform preparation for `rehearsal terraform` and `rehearsal build`.
# It loads the dev tenant's non-secret Auth0 identifiers, primes the SSH agent
# used by the Proxmox provider, verifies the PVE host, then runs Terraform in the
# maintained root. Secret values are deliberately handled by `rehearsal sync`.

if [[ -n "${_REHEARSAL_TERRAFORM_SOURCED:-}" ]]; then
  return
fi
_REHEARSAL_TERRAFORM_SOURCED=1

_TF_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
_TF_REPO_ROOT="$(cd -- "${_TF_LIB_DIR}/../../../../.." && pwd)"
TERRAFORM_DIR="${TERRAFORM_DIR:-${_TF_REPO_ROOT}/infra/deployment/proxmox/terraform}"
DEV_BACKEND_ENV="${DEV_BACKEND_ENV:-${_TF_REPO_ROOT}/infra/env/dev/.backend.env}"

_terraform_read_env_value() {
  local key="$1" file="$2" line value
  line="$(grep -E "^${key}=" "${file}" | tail -n1 || true)"
  [[ -n "${line}" ]] || return 1
  value="${line#*=}"
  value="${value%$'\r'}"
  value="${value#[\"\']}"; value="${value%[\"\']}"
  [[ -n "${value}" ]] || return 1
  printf '%s' "${value}"
}

rehearsal_prepare_terraform() {
  [[ "${_REHEARSAL_TERRAFORM_PREPARED:-0}" == 1 ]] && return 0
  [[ -f "${DEV_BACKEND_ENV}" ]] || die "dev backend env not found: ${DEV_BACKEND_ENV} (set DEV_BACKEND_ENV=)"
  [[ -d "${TERRAFORM_DIR}" ]] || die "Terraform root not found: ${TERRAFORM_DIR}"
  command -v terraform >/dev/null 2>&1 || die "terraform not found on this box"

  local source_key tf_name value auth0_domain="" auth0_mgmt_domain=""
  while IFS=: read -r source_key tf_name; do
    value="$(_terraform_read_env_value "${source_key}" "${DEV_BACKEND_ENV}")" \
      || die "${source_key} is missing or empty in ${DEV_BACKEND_ENV}"
    export "TF_VAR_${tf_name}=${value}"
    [[ "${tf_name}" == auth0_domain ]] && auth0_domain="${value}"
    [[ "${tf_name}" == auth0_mgmt_domain ]] && auth0_mgmt_domain="${value}"
  done <<'MAPPING'
FLOWFORM_AUTH0_DOMAIN:auth0_domain
FLOWFORM_AUTH0_AUDIENCE:auth0_audience
FLOWFORM_AUTH0_CLIENT_ID:auth0_client_id
FLOWFORM_AUTH0_MGMT_DOMAIN:auth0_mgmt_domain
FLOWFORM_AUTH0_MGMT_ID:auth0_mgmt_id
MAPPING
  log "Terraform Auth0 identifiers loaded from ${DEV_BACKEND_ENV#"${_TF_REPO_ROOT}/"}"
  log "issuer: ${auth0_domain} | management tenant: ${auth0_mgmt_domain}"

  [[ "${SKIP_SSH_PREFLIGHT:-0}" == 1 ]] && {
    log "Terraform SSH preflight skipped (SKIP_SSH_PREFLIGHT=1)"
    _REHEARSAL_TERRAFORM_PREPARED=1
    return 0
  }
  command -v ssh-add >/dev/null 2>&1 || die "ssh-add not found"
  if [[ -z "${SSH_AUTH_SOCK:-}" ]]; then
    log "no ssh-agent in this shell — starting one for this Terraform run"
    eval "$(ssh-agent -s)" >/dev/null || die "failed to start ssh-agent"
  fi

  local want
  want="$(ssh-keygen -y -f "${PVE_SSH_KEY}" 2>/dev/null | awk '{print $1" "$2}')" \
    || die "could not read the PVE SSH key: ${PVE_SSH_KEY}"
  if ! ssh-add -L 2>/dev/null | awk '{print $1" "$2}' | grep -qxF "${want}"; then
    ssh-add "${PVE_SSH_KEY}" >/dev/null 2>&1 \
      || die "ssh-add failed for ${PVE_SSH_KEY}"
    log "loaded PVE key into the Terraform SSH agent"
  fi

  pve_ssh true >/dev/null 2>&1 \
    || die "${PVE_USER}@${PVE_HOST} is not reachable with ${PVE_SSH_KEY}"
  log "Terraform SSH preflight OK — ${PVE_USER}@${PVE_HOST} reachable"
  _REHEARSAL_TERRAFORM_PREPARED=1
}

rehearsal_terraform() {
  rehearsal_prepare_terraform
  terraform -chdir="${TERRAFORM_DIR}" "$@"
}
