#!/usr/bin/env bash
set -Eeuo pipefail

# Render app.user-data.yaml.template -> app.user-data.rendered.yaml by injecting
# the base64 of the REAL repo files (single source of truth). Run this whenever
# bootstrap-app.sh or docker-compose.app.yml changes; create-vms.sh runs it too.
#
# Why a generator (not a committed base64 blob): the app box is offline, so the
# bootstrap script + compose file must travel INSIDE cloud-init. Keeping them as
# their real repo files and injecting at render time means there is exactly one
# copy to maintain — no drift between "the script" and "the baked script".
#
# The .rendered.yaml is a BUILD ARTIFACT (git-ignored). Never edit it by hand.

log() { printf '[render-user-data] %s\n' "$*"; }
die() { printf '[render-user-data] ERROR: %s\n' "$*" >&2; exit 1; }

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

TEMPLATE="${HERE}/app.user-data.yaml.template"
RENDERED="${HERE}/app.user-data.rendered.yaml"

# The render pulls three REAL repo files that live OUTSIDE infra/rehearsal/
# (infra/scripts/bootstrap/, infra/docker/). Two run contexts:
#   - dev machine: full repo checked out → repo root is four dirs up from here.
#   - PVE host: run from a synced copy. Sync from the REPO ROOT (see README) so
#     these subtrees exist, or pass REPO_ROOT=/path explicitly.
# Fail loud with a clear message if the sources aren't reachable.
REPO_ROOT="${REPO_ROOT:-$(cd -- "${HERE}/../../../.." && pwd)}"

BOOTSTRAP_APP="${REPO_ROOT}/infra/scripts/bootstrap/bootstrap-app.sh"
COMPOSE_APP="${REPO_ROOT}/infra/docker/docker-compose.app.yml"
CA_CRT="${REPO_ROOT}/infra/rehearsal/tls-shim/ca/rehearsal-ca.crt"

for f in "${TEMPLATE}" "${BOOTSTRAP_APP}" "${COMPOSE_APP}" "${CA_CRT}"; do
  [[ -f "${f}" ]] || die "missing source file: ${f} (REPO_ROOT=${REPO_ROOT}; sync from the repo root or set REPO_ROOT=)"
done

# base64 -w0 = single line (cloud-init wants the content on one logical line).
b64() { base64 -w0 "$1"; }

CA_B64="$(b64 "${CA_CRT}")"
BOOTSTRAP_B64="$(b64 "${BOOTSTRAP_APP}")"
COMPOSE_B64="$(b64 "${COMPOSE_APP}")"

# Use a tmp file + mv so a failed render never leaves a half-written artifact.
tmp="$(mktemp "${RENDERED}.tmp.XXXXXX")"
# shellcheck disable=SC2064
trap "rm -f '${tmp}'" EXIT

# Substitute via awk (base64 has no '/' issues, but may be long; awk handles it
# without sed's delimiter/length headaches). One placeholder per line in the tpl.
awk \
  -v ca="${CA_B64}" \
  -v boot="${BOOTSTRAP_B64}" \
  -v comp="${COMPOSE_B64}" '
  {
    gsub(/__REHEARSAL_CA_CRT_B64__/, ca)
    gsub(/__BOOTSTRAP_APP_SH_B64__/, boot)
    gsub(/__DOCKER_COMPOSE_APP_B64__/, comp)
    print
  }
' "${TEMPLATE}" > "${tmp}"

# Fail loud if any placeholder survived (typo / renamed marker).
if grep -q '__[A-Z0-9_]*_B64__' "${tmp}"; then
  die "unsubstituted placeholder remains in render — check template markers"
fi

mv "${tmp}" "${RENDERED}"
trap - EXIT
log "wrote ${RENDERED}"
log "  ca=${CA_CRT}"
log "  bootstrap=${BOOTSTRAP_APP}"
log "  compose=${COMPOSE_APP}"
