#!/usr/bin/env bash
set -Eeuo pipefail

# Render every *.yaml.template in this dir -> *.yaml.rendered.yaml by injecting the
# base64 of the REAL repo files (single source of truth). Run whenever any of the
# referenced repo files change; Terraform uploads the result during apply.
#
# Why a generator (not committed base64 blobs): the private VMs are offline, so
# the bootstrap scripts + compose/config files must travel INSIDE cloud-init.
# Keeping them as their real repo files and injecting at render time means there
# is exactly one copy of each to maintain — no drift between "the script" and
# "the baked script".
#
# Adding a new placeholder = one line in the PLACEHOLDERS table below. A template
# uses whatever subset of placeholders it needs; any __*_B64__ left unsubstituted
# after a render is a hard error (typo / renamed marker).
#
# The *.rendered.yaml files are BUILD ARTIFACTS (git-ignored). Never edit by hand.

log() { printf '[render-cloud-init] %s\n' "$*"; }
die() { printf '[render-cloud-init] ERROR: %s\n' "$*" >&2; exit 1; }

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/cloud-init"

# The render runs from the local checkout; Terraform uploads its resulting
# snippets, so no repository checkout is needed on the Proxmox host.
REPO_ROOT="${REPO_ROOT:-$(cd -- "${HERE}/../../../../.." && pwd)}"

# placeholder marker  ->  repo-relative source file.
# Keep markers in sync with the *.template files that reference them.
declare -A PLACEHOLDERS=(
  [__REHEARSAL_CA_CRT_B64__]="infra/containers/rehearsal/services/tls-shim/ca/rehearsal-ca.crt"
  [__BOOTSTRAP_APP_SH_B64__]="infra/deployment/bootstrap/bootstrap-app.sh"
  [__AWS_CLI_RETRY_SH_B64__]="infra/deployment/bootstrap/aws-cli-retry.sh"
  [__DOCKER_COMPOSE_APP_B64__]="infra/containers/deployment/compose/compose.app.yml"
  [__DOCKER_COMPOSE_APP_REHEARSAL_B64__]="infra/containers/rehearsal/compose/compose.app.rehearsal.yml"
  [__BOOTSTRAP_PROXY_SH_B64__]="infra/deployment/bootstrap/bootstrap-proxy.sh"
  [__DOCKER_COMPOSE_PROXY_B64__]="infra/containers/deployment/compose/compose.proxy.yml"
  [__DOCKER_COMPOSE_PROXY_REHEARSAL_B64__]="infra/containers/rehearsal/compose/compose.proxy.rehearsal.yml"
  [__CADDYFILE_PROXY_REHEARSAL_B64__]="infra/containers/rehearsal/services/caddy/Caddyfile.proxy"
  [__SQUID_CONF_B64__]="infra/containers/deployment/services/squid/squid.conf"
  [__SQUID_ALLOWED_DOMAINS_REHEARSAL_B64__]="infra/containers/rehearsal/services/squid/allowed-domains.txt"
  [__DOCKER_COMPOSE_LOCALSTACK_B64__]="infra/containers/rehearsal/compose/compose.localstack.yml"
  [__LOCALSTACK_SEED_SH_B64__]="infra/containers/rehearsal/services/localstack/seed-localstack.sh"
  [__RUNTIME_PARAMETER_CONTRACT_B64__]="infra/deployment/config/runtime-parameter-contract.json"
  [__DOCKER_COMPOSE_REGISTRY_B64__]="infra/containers/rehearsal/compose/compose.registry.yml"
  [__DOCKER_COMPOSE_TLS_SHIM_B64__]="infra/containers/rehearsal/compose/compose.tls-shim.yml"
  [__TLS_SHIM_CADDYFILE_B64__]="infra/containers/rehearsal/services/tls-shim/Caddyfile"
  [__LOCALSTACK_CRT_B64__]="infra/containers/rehearsal/services/tls-shim/ca/localstack.crt"
  [__LOCALSTACK_KEY_B64__]="infra/containers/rehearsal/services/tls-shim/ca/localstack.key"
)

# base64 -w0 = single line (cloud-init wants the content on one logical line).
b64() { base64 -w0 "$1"; }

# Precompute the base64 of every source file once (only those that exist are
# required by whichever template references them; we check per-template below).
declare -A B64VAL
for marker in "${!PLACEHOLDERS[@]}"; do
  src="${REPO_ROOT}/${PLACEHOLDERS[$marker]}"
  [[ -f "${src}" ]] || die "missing source file: ${src} (REPO_ROOT=${REPO_ROOT}; sync from the repo root or set REPO_ROOT=)"
  B64VAL["${marker}"]="$(b64 "${src}")"
done

render_one() {
  local tpl="$1"
  local out="${tpl%.template}.rendered.yaml"
  # app.user-data.yaml.template -> app.user-data.rendered.yaml
  out="${tpl%.yaml.template}.rendered.yaml"

  local tmp; tmp="$(mktemp "${out}.tmp.XXXXXX")"
  # shellcheck disable=SC2064
  trap "rm -f '${tmp}'" RETURN

  # Build an awk program that gsubs every known marker. Pass values as -v args.
  local awk_args=() awk_prog="{"
  local i=0
  for marker in "${!B64VAL[@]}"; do
    awk_args+=(-v "v${i}=${B64VAL[$marker]}")
    awk_prog+="gsub(/${marker}/, v${i});"
    ((i++)) || true
  done
  awk_prog+="print}"

  awk "${awk_args[@]}" "${awk_prog}" "${tpl}" > "${tmp}"

  if grep -q '__[A-Z0-9_]*_B64__' "${tmp}"; then
    die "unsubstituted placeholder remains in $(basename "${out}") — add it to PLACEHOLDERS or fix the marker"
  fi

  mv "${tmp}" "${out}"
  trap - RETURN
  log "wrote ${out}"
}

shopt -s nullglob
templates=("${HERE}"/*.yaml.template)
shopt -u nullglob
[[ ${#templates[@]} -gt 0 ]] || die "no *.yaml.template files in ${HERE}"

for tpl in "${templates[@]}"; do
  render_one "${tpl}"
done
