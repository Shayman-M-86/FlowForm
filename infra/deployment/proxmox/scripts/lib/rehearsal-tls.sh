#!/usr/bin/env bash
# Machine-local TLS material for the Proxmox rehearsal.
#
# The CA is a workstation trust anchor and must survive VM rebuilds, but its
# private key must not be committed. This library creates the complete local
# set on first use, preserves a valid existing CA, and repairs missing, expired,
# or mismatched leaf pairs under that CA.

if [[ -n "${_REHEARSAL_TLS_SOURCED:-}" ]]; then
  return
fi
_REHEARSAL_TLS_SOURCED=1

_TLS_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
_TLS_REPO_ROOT="$(cd -- "${_TLS_LIB_DIR}/../../../../.." && pwd)"

REHEARSAL_TLS_CA_DIR="${REHEARSAL_TLS_CA_DIR:-${_TLS_REPO_ROOT}/infra/containers/runtime/proxmox/rehearsal/services/tls-shim/ca}"
REHEARSAL_TLS_API_DIR="${REHEARSAL_TLS_API_DIR:-${_TLS_REPO_ROOT}/infra/containers/runtime/proxmox/rehearsal/services/caddy/certs}"
REHEARSAL_TLS_SAN_CONFIG="${REHEARSAL_TLS_SAN_CONFIG:-${REHEARSAL_TLS_CA_DIR}/san.cnf}"
REHEARSAL_TLS_DAYS="${REHEARSAL_TLS_DAYS:-3650}"
REHEARSAL_TLS_MIN_VALIDITY_SECONDS="${REHEARSAL_TLS_MIN_VALIDITY_SECONDS:-2592000}"
REHEARSAL_TLS_API_DOMAIN="${REHEARSAL_TLS_API_DOMAIN:-api.localstack.test}"

_tls_ca_key() { printf '%s/rehearsal-ca.key' "${REHEARSAL_TLS_CA_DIR}"; }
_tls_ca_cert() { printf '%s/rehearsal-ca.crt' "${REHEARSAL_TLS_CA_DIR}"; }
_tls_localstack_key() { printf '%s/localstack.key' "${REHEARSAL_TLS_CA_DIR}"; }
_tls_localstack_cert() { printf '%s/localstack.crt' "${REHEARSAL_TLS_CA_DIR}"; }
_tls_api_key() { printf '%s/api.key' "${REHEARSAL_TLS_API_DIR}"; }
_tls_api_cert() { printf '%s/api.crt' "${REHEARSAL_TLS_API_DIR}"; }

_tls_key_digest() { # key
  openssl pkey -in "$1" -pubout -outform DER 2>/dev/null | sha256sum | awk '{print $1}'
}

_tls_cert_key_digest() { # certificate
  openssl x509 -in "$1" -pubkey -noout 2>/dev/null \
    | openssl pkey -pubin -outform DER 2>/dev/null \
    | sha256sum | awk '{print $1}'
}

_tls_ca_material_valid() { # key certificate
  local key="$1" cert="$2" key_digest cert_digest
  [[ -s "${key}" && -s "${cert}" ]] || return 1
  openssl pkey -in "${key}" -check -noout >/dev/null 2>&1 || return 1
  openssl x509 -in "${cert}" -noout >/dev/null 2>&1 || return 1
  openssl x509 -in "${cert}" -checkend "${REHEARSAL_TLS_MIN_VALIDITY_SECONDS}" -noout >/dev/null 2>&1 || return 1
  key_digest="$(_tls_key_digest "${key}")" || return 1
  cert_digest="$(_tls_cert_key_digest "${cert}")" || return 1
  [[ -n "${key_digest}" && "${key_digest}" == "${cert_digest}" ]] || return 1
  openssl verify -CAfile "${cert}" "${cert}" >/dev/null 2>&1
}

_tls_leaf_material_valid() { # key certificate CA-certificate hostname...
  local key="$1" cert="$2" ca_cert="$3" key_digest cert_digest hostname
  shift 3
  [[ -s "${key}" && -s "${cert}" && -s "${ca_cert}" && $# -gt 0 ]] || return 1
  openssl pkey -in "${key}" -check -noout >/dev/null 2>&1 || return 1
  openssl x509 -in "${cert}" -noout >/dev/null 2>&1 || return 1
  openssl x509 -in "${cert}" -checkend "${REHEARSAL_TLS_MIN_VALIDITY_SECONDS}" -noout >/dev/null 2>&1 || return 1
  key_digest="$(_tls_key_digest "${key}")" || return 1
  cert_digest="$(_tls_cert_key_digest "${cert}")" || return 1
  [[ -n "${key_digest}" && "${key_digest}" == "${cert_digest}" ]] || return 1
  openssl verify -CAfile "${ca_cert}" "${cert}" >/dev/null 2>&1 || return 1
  for hostname in "$@"; do
    openssl x509 -in "${cert}" -checkhost "${hostname}" -noout >/dev/null 2>&1 || return 1
  done
}

_tls_localstack_hostnames() {
  awk -F= '
    /^[[:space:]]*DNS\.[0-9]+[[:space:]]*=/ {
      value=$2
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      if (value != "") print value
    }
  ' "${REHEARSAL_TLS_SAN_CONFIG}"
}

_tls_random_serial() {
  printf '0x%s' "$(openssl rand -hex 16)"
}

_tls_generate_ca() { # output-key output-certificate
  openssl req -x509 -newkey rsa:3072 -nodes -sha256 \
    -days "${REHEARSAL_TLS_DAYS}" \
    -subj '/CN=FlowForm Rehearsal CA (machine-local)/O=FlowForm Rehearsal' \
    -addext 'basicConstraints=critical,CA:TRUE' \
    -addext 'keyUsage=critical,keyCertSign,cRLSign' \
    -addext 'subjectKeyIdentifier=hash' \
    -keyout "$1" \
    -out "$2" \
    >/dev/null 2>&1
}

_tls_generate_localstack_leaf() { # output-key output-certificate CA-key CA-certificate work-dir
  local key="$1" cert="$2" ca_key="$3" ca_cert="$4" work_dir="$5" csr
  csr="${work_dir}/localstack.csr"
  openssl req -new -newkey rsa:2048 -nodes -sha256 \
    -config "${REHEARSAL_TLS_SAN_CONFIG}" \
    -keyout "${key}" \
    -out "${csr}" \
    >/dev/null 2>&1
  openssl x509 -req -sha256 \
    -in "${csr}" \
    -CA "${ca_cert}" \
    -CAkey "${ca_key}" \
    -set_serial "$(_tls_random_serial)" \
    -days "${REHEARSAL_TLS_DAYS}" \
    -extfile "${REHEARSAL_TLS_SAN_CONFIG}" \
    -extensions v3_req \
    -out "${cert}" \
    >/dev/null 2>&1
}

_tls_generate_api_leaf() { # output-key output-certificate CA-key CA-certificate work-dir
  local key="$1" cert="$2" ca_key="$3" ca_cert="$4" work_dir="$5" csr extensions
  csr="${work_dir}/api.csr"
  extensions="${work_dir}/api-extensions.cnf"
  cat >"${extensions}" <<EOF
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:${REHEARSAL_TLS_API_DOMAIN}
EOF
  openssl req -new -newkey rsa:2048 -nodes -sha256 \
    -keyout "${key}" \
    -subj "/CN=${REHEARSAL_TLS_API_DOMAIN}" \
    -out "${csr}" \
    >/dev/null 2>&1
  openssl x509 -req -sha256 \
    -in "${csr}" \
    -CA "${ca_cert}" \
    -CAkey "${ca_key}" \
    -set_serial "$(_tls_random_serial)" \
    -days "${REHEARSAL_TLS_DAYS}" \
    -extfile "${extensions}" \
    -out "${cert}" \
    >/dev/null 2>&1
}

_tls_install_file() { # mode source destination
  local mode="$1" source="$2" destination="$3" temporary
  temporary="$(mktemp "${destination}.new.XXXXXX")" \
    || die "could not create temporary TLS file beside ${destination}"
  if ! install -m "${mode}" "${source}" "${temporary}"; then
    rm -f -- "${temporary}"
    die "could not install TLS material at ${destination}"
  fi
  mv -f -- "${temporary}" "${destination}"
}

_tls_install_pair() { # staged-key staged-certificate destination-key destination-certificate
  _tls_install_file 0600 "$1" "$3"
  _tls_install_file 0644 "$2" "$4"
}

_tls_generate_complete_set() (
  set -Eeuo pipefail
  umask 077
  local work ca_key ca_cert localstack_key localstack_cert api_key api_cert
  local -a localstack_hosts
  work="$(mktemp -d "${TMPDIR:-/tmp}/flowform-rehearsal-tls.XXXXXX")" \
    || die "could not create temporary TLS work directory"
  trap 'rm -rf -- "${work}"' EXIT
  ca_key="${work}/rehearsal-ca.key"
  ca_cert="${work}/rehearsal-ca.crt"
  localstack_key="${work}/localstack.key"
  localstack_cert="${work}/localstack.crt"
  api_key="${work}/api.key"
  api_cert="${work}/api.crt"
  mapfile -t localstack_hosts < <(_tls_localstack_hostnames)
  (( ${#localstack_hosts[@]} > 0 )) || die "no DNS names found in ${REHEARSAL_TLS_SAN_CONFIG}"

  _tls_generate_ca "${ca_key}" "${ca_cert}" \
    || die "could not generate the rehearsal CA"
  _tls_generate_localstack_leaf "${localstack_key}" "${localstack_cert}" "${ca_key}" "${ca_cert}" "${work}" \
    || die "could not generate the LocalStack TLS leaf"
  _tls_generate_api_leaf "${api_key}" "${api_cert}" "${ca_key}" "${ca_cert}" "${work}" \
    || die "could not generate the proxy API TLS leaf"

  _tls_ca_material_valid "${ca_key}" "${ca_cert}" \
    || die "generated rehearsal CA failed validation"
  _tls_leaf_material_valid "${localstack_key}" "${localstack_cert}" "${ca_cert}" "${localstack_hosts[@]}" \
    || die "generated LocalStack TLS leaf failed validation"
  _tls_leaf_material_valid "${api_key}" "${api_cert}" "${ca_cert}" "${REHEARSAL_TLS_API_DOMAIN}" \
    || die "generated proxy API TLS leaf failed validation"

  _tls_install_pair "${ca_key}" "${ca_cert}" "$(_tls_ca_key)" "$(_tls_ca_cert)"
  _tls_install_pair "${localstack_key}" "${localstack_cert}" "$(_tls_localstack_key)" "$(_tls_localstack_cert)"
  _tls_install_pair "${api_key}" "${api_cert}" "$(_tls_api_key)" "$(_tls_api_cert)"
)

_tls_regenerate_localstack_leaf() (
  set -Eeuo pipefail
  umask 077
  local work key cert
  local -a localstack_hosts
  work="$(mktemp -d "${TMPDIR:-/tmp}/flowform-rehearsal-tls.XXXXXX")" \
    || die "could not create temporary TLS work directory"
  trap 'rm -rf -- "${work}"' EXIT
  key="${work}/localstack.key"
  cert="${work}/localstack.crt"
  mapfile -t localstack_hosts < <(_tls_localstack_hostnames)
  (( ${#localstack_hosts[@]} > 0 )) || die "no DNS names found in ${REHEARSAL_TLS_SAN_CONFIG}"
  _tls_generate_localstack_leaf "${key}" "${cert}" "$(_tls_ca_key)" "$(_tls_ca_cert)" "${work}" \
    || die "could not generate the LocalStack TLS leaf"
  _tls_leaf_material_valid "${key}" "${cert}" "$(_tls_ca_cert)" "${localstack_hosts[@]}" \
    || die "generated LocalStack TLS leaf failed validation"
  _tls_install_pair "${key}" "${cert}" "$(_tls_localstack_key)" "$(_tls_localstack_cert)"
)

_tls_regenerate_api_leaf() (
  set -Eeuo pipefail
  umask 077
  local work key cert
  work="$(mktemp -d "${TMPDIR:-/tmp}/flowform-rehearsal-tls.XXXXXX")" \
    || die "could not create temporary TLS work directory"
  trap 'rm -rf -- "${work}"' EXIT
  key="${work}/api.key"
  cert="${work}/api.crt"
  _tls_generate_api_leaf "${key}" "${cert}" "$(_tls_ca_key)" "$(_tls_ca_cert)" "${work}" \
    || die "could not generate the proxy API TLS leaf"
  _tls_leaf_material_valid "${key}" "${cert}" "$(_tls_ca_cert)" "${REHEARSAL_TLS_API_DOMAIN}" \
    || die "generated proxy API TLS leaf failed validation"
  _tls_install_pair "${key}" "${cert}" "$(_tls_api_key)" "$(_tls_api_cert)"
)

rehearsal_ensure_tls() {
  [[ "${_REHEARSAL_TLS_PREPARED:-0}" == 1 ]] && return 0
  local tool ca_key ca_cert localstack_key localstack_cert api_key api_cert repaired=0
  local -a localstack_hosts
  for tool in openssl sha256sum awk install mktemp; do
    command -v "${tool}" >/dev/null 2>&1 || die "${tool} is required to prepare rehearsal TLS material"
  done
  [[ "${REHEARSAL_TLS_DAYS}" =~ ^[1-9][0-9]*$ ]] \
    || die "REHEARSAL_TLS_DAYS must be a positive integer"
  [[ "${REHEARSAL_TLS_MIN_VALIDITY_SECONDS}" =~ ^[0-9]+$ ]] \
    || die "REHEARSAL_TLS_MIN_VALIDITY_SECONDS must be a non-negative integer"
  [[ -r "${REHEARSAL_TLS_SAN_CONFIG}" ]] \
    || die "LocalStack TLS SAN config not readable: ${REHEARSAL_TLS_SAN_CONFIG}"
  mkdir -p -- "${REHEARSAL_TLS_CA_DIR}" "${REHEARSAL_TLS_API_DIR}"

  ca_key="$(_tls_ca_key)"
  ca_cert="$(_tls_ca_cert)"
  localstack_key="$(_tls_localstack_key)"
  localstack_cert="$(_tls_localstack_cert)"
  api_key="$(_tls_api_key)"
  api_cert="$(_tls_api_cert)"
  mapfile -t localstack_hosts < <(_tls_localstack_hostnames)
  (( ${#localstack_hosts[@]} > 0 )) || die "no DNS names found in ${REHEARSAL_TLS_SAN_CONFIG}"

  if [[ ! -e "${ca_key}" && ! -e "${ca_cert}" ]]; then
    phase "prepare machine-local rehearsal TLS trust anchor and leaf certificates"
    _tls_generate_complete_set
    success "created machine-local rehearsal CA and leaf certificates"
    log "trust anchor: ${ca_cert#"${_TLS_REPO_ROOT}/"}"
    _REHEARSAL_TLS_PREPARED=1
    return 0
  fi

  _tls_ca_material_valid "${ca_key}" "${ca_cert}" \
    || die "existing rehearsal CA pair is incomplete, invalid, mismatched, or near expiry: ${ca_cert}. Preserve it for inspection and rotate the trust anchor deliberately; it will not be overwritten automatically."

  if ! _tls_leaf_material_valid "${localstack_key}" "${localstack_cert}" "${ca_cert}" "${localstack_hosts[@]}"; then
    phase "refresh LocalStack TLS leaf under the existing rehearsal CA"
    _tls_regenerate_localstack_leaf
    repaired=1
  fi
  if ! _tls_leaf_material_valid "${api_key}" "${api_cert}" "${ca_cert}" "${REHEARSAL_TLS_API_DOMAIN}"; then
    phase "refresh proxy API TLS leaf under the existing rehearsal CA"
    _tls_regenerate_api_leaf
    repaired=1
  fi

  chmod 0600 -- "${ca_key}" "${localstack_key}" "${api_key}"
  chmod 0644 -- "${ca_cert}" "${localstack_cert}" "${api_cert}"
  if (( repaired == 1 )); then
    success "repaired rehearsal leaf certificates without changing the CA trust anchor"
  else
    log "machine-local rehearsal TLS material is valid"
  fi
  _REHEARSAL_TLS_PREPARED=1
}
