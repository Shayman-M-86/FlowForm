#!/usr/bin/env bash
# Shared library for the workstation-side `rehearsal` dispatcher and its
# subcommands (build, verify, logs, sync, rotate). Sourced — never executed.
#
# It owns exactly the surface the old standalone scripts each re-implemented:
# structured log/die, the canonical PVE_*/BRIDGE_* connection variables, the two
# SSH helpers (jump-host + guest-through-jump), the temporary-bridge acquire/use/
# release dance, and the role -> IP/container table. Centralising these removes
# four near-identical copies and the env-var name drift between them
# (PROXMOX_SSH_TARGET vs PVE_HOST, BRIDGE_ADDR vs PROXMOX_TEMP_BRIDGE_CIDR, ...).
#
# WHY the bridge dance lives here: the rehearsal VMs sit on vmbr10
# (10.10.10.0/24), isolated by design — the Proxmox host holds no address on it,
# so there is no route in. Every subcommand that touches a VM must temporarily
# add 10.10.10.1/24 to vmbr10, tunnel through the PVE host, and remove the
# address again on exit so the isolation invariant survives a Ctrl-C. One
# implementation now guarantees that for all of them.

if [[ -n "${_REHEARSAL_COMMON_SOURCED:-}" ]]; then
  return
fi
_REHEARSAL_COMMON_SOURCED=1

# The dispatcher sets this so log/die carry the subcommand (e.g. "rehearsal
# build"). Falls back to a bare tag if sourced directly.
REHEARSAL_SUBCOMMAND="${REHEARSAL_SUBCOMMAND:-rehearsal}"

# Workstation-side control-plane logs use the same shape as the guest bootstrap
# logs. Keep command payloads (Terraform output, Docker logs, JSON) untouched:
# callers may parse them, and Terraform also owns its interactive terminal UI.
#
# Colour policy:
#   REHEARSAL_COLOR=auto   colour only when the destination is a terminal
#   REHEARSAL_COLOR=always force ANSI colour
#   REHEARSAL_COLOR=never  never emit ANSI colour
# NO_COLOR also disables colour, following https://no-color.org/.
REHEARSAL_COLOR="${REHEARSAL_COLOR:-auto}"

_rehearsal_colour_enabled() { # output-fd
  local fd="$1"
  [[ -z "${NO_COLOR:-}" ]] || return 1
  case "${REHEARSAL_COLOR}" in
    always) return 0 ;;
    never)  return 1 ;;
    auto)   [[ -t "${fd}" ]] ;;
    *)      return 1 ;;
  esac
}

_rehearsal_emit() { # output-fd LEVEL COMPONENT MESSAGE...
  local fd="$1" level="$2" component="$3"
  shift 3
  local timestamp colour="" reset=""
  timestamp="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  if _rehearsal_colour_enabled "${fd}"; then
    reset=$'\033[0m'
    case "${level}" in
      PHASE)   colour=$'\033[1;35m' ;;
      INFO)    colour=$'\033[0;36m' ;;
      SUCCESS) colour=$'\033[1;32m' ;;
      WARN)    colour=$'\033[1;33m' ;;
      ERROR)   colour=$'\033[1;31m' ;;
    esac
  fi
  printf '%s | %b%-7s%b | %-20s | %s\n' \
    "${timestamp}" "${colour}" "${level}" "${reset}" "${component}" "$*" >&"${fd}"
}

log() {
  case "$*" in
    WARNING:\ *) warn "${*#WARNING: }" ;;
    ERROR:\ *)   error "${*#ERROR: }" ;;
    *)           _rehearsal_emit 2 INFO "${REHEARSAL_SUBCOMMAND}" "$*" ;;
  esac
}
phase()   { _rehearsal_emit 2 PHASE   "${REHEARSAL_SUBCOMMAND}" "$*"; }
success() { _rehearsal_emit 2 SUCCESS "${REHEARSAL_SUBCOMMAND}" "$*"; }
warn()    { _rehearsal_emit 2 WARN    "${REHEARSAL_SUBCOMMAND}" "$*"; }
error()   { _rehearsal_emit 2 ERROR   "${REHEARSAL_SUBCOMMAND}" "$*"; }
die()     { error "$*"; exit 1; }

rehearsal_result() { # PASS|FAIL message...
  local result="$1"; shift
  case "${result}" in
    PASS) _rehearsal_emit 1 SUCCESS "rehearsal verify" "$*" ;;
    FAIL) _rehearsal_emit 1 ERROR   "rehearsal verify" "$*" ;;
    *)    _rehearsal_emit 1 INFO    "rehearsal verify" "$*" ;;
  esac
}

rehearsal_replay_log() { # component file
  local component="$1" file="$2" line
  while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ "${line}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z[[:space:]]\| ]]; then
      # Bootstrap and publisher lines already carry their real occurrence time.
      printf '%s\n' "${line}"
    else
      _rehearsal_emit 1 INFO "${component}" "${line}"
    fi
  done <"${file}"
}

rehearsal_prompt() { # message (intentionally no trailing newline)
  local timestamp colour="" reset=""
  timestamp="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  if _rehearsal_colour_enabled 2; then
    colour=$'\033[1;33m'
    reset=$'\033[0m'
  fi
  printf '%s | %b%-7s%b | %-20s | %s ' \
    "${timestamp}" "${colour}" WARN "${reset}" "${REHEARSAL_SUBCOMMAND}" "$*" >&2
}

# --- canonical connection variables (all overridable via env) ----------------
# One name per concept. These replace the divergent names the standalone scripts
# used; there is no PROXMOX_* fallback — callers use these.
PVE_HOST="${PVE_HOST:-192.168.68.88}"
PVE_USER="${PVE_USER:-root}"
PVE_SSH_KEY="${PVE_SSH_KEY:-${HOME}/.ssh/proxmox_codex}"
GUEST_USER="${GUEST_USER:-ec2-user}"
# Private bridge + the temporary management address. Fixed in
# terraform/virtual-machines.tf; keep in sync with the ipconfig blocks there.
BRIDGE="${BRIDGE:-vmbr10}"
BRIDGE_CIDR="${BRIDGE_CIDR:-10.10.10.1/24}"
# Per-call SSH connect timeout (seconds); individual subcommands may override.
PVE_SSH_CONNECT_TIMEOUT="${PVE_SSH_CONNECT_TIMEOUT:-8}"

rehearsal_preflight() {
  command -v ssh >/dev/null 2>&1 || die "ssh not found on this box"
  [[ -r "${PVE_SSH_KEY}" ]] || die "Proxmox SSH key not readable: ${PVE_SSH_KEY}"
  [[ "${PVE_HOST}" =~ ^[A-Za-z0-9._:-]+$ ]] || die "PVE_HOST contains unsupported characters"
  [[ "${PVE_USER}" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]] || die "PVE_USER contains unsupported characters"
  [[ "${GUEST_USER}" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]] || die "GUEST_USER contains unsupported characters"
  [[ "${BRIDGE}" =~ ^[A-Za-z0-9_.:-]+$ ]] || die "BRIDGE contains unsupported characters"
  [[ "${BRIDGE_CIDR}" =~ ^[0-9.]+/[0-9]{1,2}$ ]] || die "BRIDGE_CIDR must be an IPv4 CIDR"
}

rehearsal_preflight_pve_tools() {
  local missing
  missing="$(pve_ssh 'for tool in python3 openssl tar sha256sum; do command -v "$tool" >/dev/null 2>&1 || printf "%s " "$tool"; done')" \
    || die "could not check required tools on ${PVE_USER}@${PVE_HOST}"
  [[ -z "${missing}" ]] \
    || die "PVE host is missing required tool(s): ${missing}. Install them before rebuilding; no VMs have been destroyed by this preflight."
}

# --- role -> IP / container resolver ------------------------------------------
# VM 230 answers to three historical names (registry/localstack/fixtures); accept
# all, resolve to one box. `fixtures` is the canonical label (matches terraform's
# localstack_fixture_template).
rehearsal_ip() {
  case "$1" in
    proxy)                        echo "10.10.10.10" ;;
    app)                          echo "10.10.10.20" ;;
    fixtures|registry|localstack) echo "10.10.10.30" ;;
    db)                           echo "10.10.10.40" ;;
    *) die "unknown rehearsal role: $1 (expected proxy, app, fixtures, or db)" ;;
  esac
}

rehearsal_default_container() {
  case "$1" in
    proxy)                        echo "flowform-proxy-caddy-1" ;;
    app)                          echo "flowform-app-backend-1" ;;
    fixtures|registry|localstack) echo "flowform-registry" ;;
    db)                           echo "flowform-db" ;;
    *) die "unknown rehearsal role: $1" ;;
  esac
}

rehearsal_bootstrap_launcher() {
  case "$1" in
    app)   echo "/opt/flowform/scripts/run-bootstrap-app.sh" ;;
    proxy) echo "/opt/flowform/scripts/run-bootstrap-proxy.sh" ;;
    db)    echo "/opt/flowform/scripts/run-bootstrap-db.sh" ;;
    *) die "role has no runtime bootstrap launcher: $1" ;;
  esac
}

# --- SSH helpers --------------------------------------------------------------
# Jump host (the Proxmox node itself). Key-checked with accept-new: the PVE host
# IS the trust anchor that matters, and its key is stable.
pve_ssh() {
  ssh -i "${PVE_SSH_KEY}" \
    -o BatchMode=yes \
    -o ConnectTimeout="${PVE_SSH_CONNECT_TIMEOUT}" \
    -o ServerAliveInterval=15 \
    -o ServerAliveCountMax=3 \
    -o StrictHostKeyChecking=accept-new \
    "${PVE_USER}@${PVE_HOST}" "$@"
}

# guest_ssh <guest-ip> <remote command...>
#
# The rehearsal VMs are rebuilt from templates and get fresh host keys every
# time, so a pinned known_hosts entry goes stale on each teardown. They are
# throwaway guests on an isolated bridge, reached only by tunnelling through the
# PVE host (which is key-checked above) — so keep their keys out of known_hosts
# entirely rather than training the operator to answer host-key warnings "yes".
guest_ssh() {
  local ip="$1"; shift
  ssh -i "${PVE_SSH_KEY}" \
    -o BatchMode=yes \
    -o ConnectTimeout="${PVE_SSH_CONNECT_TIMEOUT}" \
    -o ServerAliveInterval=15 \
    -o ServerAliveCountMax=3 \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o LogLevel=ERROR \
    -o "ProxyCommand=ssh -i ${PVE_SSH_KEY} -o BatchMode=yes -o StrictHostKeyChecking=accept-new -W %h:%p ${PVE_USER}@${PVE_HOST}" \
    "${GUEST_USER}@${ip}" "$@"
}

rehearsal_wait_for_guest() { # role [attempts] [delay_seconds]
  local role="$1" attempts="${2:-60}" delay="${3:-2}" ip attempt
  ip="$(rehearsal_ip "${role}")"
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if guest_ssh "${ip}" true >/dev/null 2>&1; then
      log "${role} VM reachable at ${GUEST_USER}@${ip}"
      return 0
    fi
    (( attempt == attempts )) && break
    sleep "${delay}"
  done
  return 1
}

rehearsal_converge() { # app|proxy|db
  local role="$1" ip launcher
  ip="$(rehearsal_ip "${role}")"
  launcher="$(rehearsal_bootstrap_launcher "${role}")"
  rehearsal_wait_for_guest "${role}" \
    "${REHEARSAL_GUEST_MAX_ATTEMPTS:-60}" \
    "${REHEARSAL_GUEST_RETRY_DELAY_SECONDS:-2}" \
    || return 1
  guest_ssh "${ip}" "sudo ${launcher}"
}

# --- temporary bridge address: acquire / release ------------------------------
# Each subcommand installs ONE cleanup trap (so it can also tear down its own
# temp dir, restart squid, etc.) and calls `rehearsal_bridge_down` from inside
# it. This mirrors how the standalone scripts already worked — a single cleanup()
# doing both — rather than trying to magically compose traps.
#
# Typical use:
#     cleanup() { rehearsal_bridge_down; rm -rf "${WORK_DIR}"; }
#     trap cleanup EXIT INT TERM HUP
#     rehearsal_bridge_up
#     ...work over the bridge...
#
# rehearsal_bridge_up adds the address only if absent (so a concurrent session's
# address is left intact); rehearsal_bridge_down removes it only if WE added it.
_rehearsal_bridge_added=0

rehearsal_bridge_up() {
  # ip -4 -o addr show prints "<idx>: <dev> inet <addr>/<len> ..."; match the
  # address without its prefix length so /24 vs a bare form both hit.
  if pve_ssh "ip -4 -o addr show dev ${BRIDGE} | grep -Fq ${BRIDGE_CIDR%%/*}/"; then
    log "${BRIDGE_CIDR} already present on ${BRIDGE} — leaving it as found"
    return 0
  fi
  pve_ssh "ip address add ${BRIDGE_CIDR} dev ${BRIDGE}" \
    || die "could not add ${BRIDGE_CIDR} to ${BRIDGE} on ${PVE_HOST}"
  _rehearsal_bridge_added=1
}

rehearsal_bridge_down() {
  if (( _rehearsal_bridge_added == 1 )); then
    pve_ssh "ip address del ${BRIDGE_CIDR} dev ${BRIDGE}" >/dev/null 2>&1 \
      || log "WARNING: could not remove ${BRIDGE_CIDR} from ${BRIDGE} — remove it by hand"
    _rehearsal_bridge_added=0
  fi
}
