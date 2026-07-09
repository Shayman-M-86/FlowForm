#!/usr/bin/env bash
set -Eeuo pipefail

# Render every *.yaml.template in this dir -> *.yaml.rendered.yaml by injecting the
# base64 of the REAL repo files (single source of truth). Run whenever any of the
# referenced repo files change; create-vms.sh runs it too.
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

log() { printf '[render-user-data] %s\n' "$*"; }
die() { printf '[render-user-data] ERROR: %s\n' "$*" >&2; exit 1; }

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# The render pulls REAL repo files that live OUTSIDE infra/rehearsal/
# (infra/scripts/bootstrap/, infra/docker/). Two run contexts:
#   - dev machine: full repo checked out → repo root is four dirs up from here.
#   - PVE host: run from a synced copy. Sync from the REPO ROOT (see README) so
#     these subtrees exist, or pass REPO_ROOT=/path explicitly.
REPO_ROOT="${REPO_ROOT:-$(cd -- "${HERE}/../../../.." && pwd)}"

# placeholder marker  ->  repo-relative source file.
# Keep markers in sync with the *.template files that reference them.
declare -A PLACEHOLDERS=(
  [__REHEARSAL_CA_CRT_B64__]="infra/rehearsal/tls-shim/ca/rehearsal-ca.crt"
  [__BOOTSTRAP_APP_SH_B64__]="infra/scripts/bootstrap/bootstrap-app.sh"
  [__DOCKER_COMPOSE_APP_B64__]="infra/docker/docker-compose.app.yml"
  [__BOOTSTRAP_PROXY_SH_B64__]="infra/scripts/bootstrap/bootstrap-proxy.sh"
  [__DOCKER_COMPOSE_PROXY_B64__]="infra/docker/docker-compose.proxy.yml"
  [__DOCKER_COMPOSE_PROXY_REHEARSAL_B64__]="infra/rehearsal/docker-compose.proxy.rehearsal.yml"
  [__CADDYFILE_PROXY_REHEARSAL_B64__]="infra/rehearsal/caddy/Caddyfile.proxy"
  [__SQUID_CONF_B64__]="infra/docker/squid/squid.conf"
  [__SQUID_ALLOWED_DOMAINS_REHEARSAL_B64__]="infra/rehearsal/squid/allowed-domains.rehearsal.txt"
  [__DOCKER_COMPOSE_REGISTRY_B64__]="infra/rehearsal/fixtures/registry/docker-compose.registry.yml"
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
