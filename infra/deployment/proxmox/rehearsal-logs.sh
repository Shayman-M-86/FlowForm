#!/usr/bin/env bash
set -Eeuo pipefail

# Tail container logs from a rehearsal VM on the private bridge.
#
# The rehearsal VMs sit on vmbr10 (10.10.10.0/24), which is isolated by design —
# the Proxmox host holds no address on it, so there is no route in. Reaching a VM
# means temporarily adding 10.10.10.1/24 to vmbr10 and jumping through the host.
# This script adds that address, uses it, and removes it again on exit, so the
# isolation invariant survives even if you Ctrl-C mid-tail.
#
# The backend emits structured JSON (FLOWFORM_LOGGING_LOG_JSON=true), where an
# unhandled exception is a single record carrying a multi-KB traceback. Piping
# raw output at a terminal is unreadable, so the default view flattens each
# record to one line and drops the traceback; --raw opts back into full JSON
# when you need the stack.
#
# Usage:
#   rehearsal-logs.sh [app|proxy|registry] [options] [-- <extra docker logs args>]
#
#   -c, --container NAME   container to read (default: the VM's main service)
#   -e, --errors           only ERROR/CRITICAL records
#   -r, --request-id ID    only records for one request_id
#   -n, --tail N           lines of history (default: 50)
#   -f, --follow           stream new records
#       --raw              unformatted docker logs output (full tracebacks)
#       --list             list containers on the VM and exit
#
# Examples:
#   rehearsal-logs.sh app -f                     # tail the backend
#   rehearsal-logs.sh app -e -n 200              # recent failures only
#   rehearsal-logs.sh app -r 350889d7-7602-...   # one request end to end
#   rehearsal-logs.sh app --raw -n 5             # full tracebacks
#   rehearsal-logs.sh proxy -c flowform-proxy-squid-1 -f

log() { printf '[rehearsal-logs] %s\n' "$*" >&2; }
die() { printf '[rehearsal-logs] ERROR: %s\n' "$*" >&2; exit 1; }

PVE_HOST="${PVE_HOST:-192.168.68.88}"
PVE_USER="${PVE_USER:-root}"
SSH_KEY="${SSH_KEY:-${HOME}/.ssh/proxmox_codex}"
GUEST_USER="${GUEST_USER:-ec2-user}"

# Private addresses are fixed in terraform/main.tf; keep in sync with the
# ipconfig blocks there.
BRIDGE="${BRIDGE:-vmbr10}"
BRIDGE_ADDR="${BRIDGE_ADDR:-10.10.10.1/24}"

target_ip() {
  case "$1" in
    proxy)    echo "10.10.10.10" ;;
    app)      echo "10.10.10.20" ;;
    registry) echo "10.10.10.30" ;;
    *)        die "unknown target: $1 (expected app, proxy, or registry)" ;;
  esac
}

default_container() {
  case "$1" in
    proxy)    echo "flowform-proxy-caddy-1" ;;
    app)      echo "flowform-app-backend-1" ;;
    registry) echo "flowform-registry" ;;
  esac
}

TARGET="app"
CONTAINER=""
TAIL="50"
FOLLOW=""
RAW=""
LIST=""
ERRORS_ONLY=""
REQUEST_ID=""
EXTRA_ARGS=()

case "${1:-}" in
  app|proxy|registry) TARGET="$1"; shift ;;
esac

while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--container)  CONTAINER="${2:?--container needs a name}"; shift 2 ;;
    -n|--tail)       TAIL="${2:?--tail needs a count}"; shift 2 ;;
    -r|--request-id) REQUEST_ID="${2:?--request-id needs an id}"; shift 2 ;;
    -e|--errors)     ERRORS_ONLY=1; shift ;;
    -f|--follow)     FOLLOW=1; shift ;;
    --raw)           RAW=1; shift ;;
    --list)          LIST=1; shift ;;
    -h|--help)       sed -n '/^# Usage:/,/^[^#]/p' "${BASH_SOURCE[0]}" | grep '^#' | sed 's/^# \{0,1\}//'; exit 0 ;;
    --)              shift; EXTRA_ARGS=("$@"); break ;;
    *)               die "unknown option: $1 (try --help)" ;;
  esac
done

[[ -f "${SSH_KEY}" ]] || die "ssh key not found: ${SSH_KEY} (set SSH_KEY=)"
command -v jq >/dev/null || [[ -n "${RAW}" ]] || die "jq not found — install it, or pass --raw"

CONTAINER="${CONTAINER:-$(default_container "${TARGET}")}"
GUEST_IP="$(target_ip "${TARGET}")"

pve_ssh() {
  ssh -i "${SSH_KEY}" -o BatchMode=yes -o ConnectTimeout=5 \
    -o StrictHostKeyChecking=accept-new "${PVE_USER}@${PVE_HOST}" "$@"
}

# The rehearsal VMs are rebuilt from templates and get fresh host keys each time,
# so a pinned known_hosts entry goes stale on every teardown and blocks the tail.
# These are throwaway guests on an isolated bridge, reached only by tunnelling
# through the Proxmox host — which IS key-checked above, and is the trust anchor
# that matters. Keep their keys out of the user's known_hosts entirely rather
# than training them to answer host-key warnings with "yes".
guest_ssh() {
  ssh -i "${SSH_KEY}" -o BatchMode=yes -o ConnectTimeout=5 \
    -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
    -o "ProxyCommand=ssh -i ${SSH_KEY} -o BatchMode=yes -o StrictHostKeyChecking=accept-new -W %h:%p ${PVE_USER}@${PVE_HOST}" \
    "${GUEST_USER}@${GUEST_IP}" "$@"
}

# Only tear down what we set up: if the address was already there (someone else
# is mid-session), leave it alone rather than cutting their route out.
BRIDGE_ADDED=""
cleanup() {
  if [[ -n "${BRIDGE_ADDED}" ]]; then
    pve_ssh "ip addr del ${BRIDGE_ADDR} dev ${BRIDGE}" >/dev/null 2>&1 \
      || log "WARNING: failed to remove ${BRIDGE_ADDR} from ${BRIDGE} — remove it by hand"
  fi
}
trap cleanup EXIT INT TERM HUP

if pve_ssh "ip -4 addr show dev ${BRIDGE} | grep -q '${BRIDGE_ADDR%%/*}/'"; then
  log "${BRIDGE_ADDR} already present on ${BRIDGE} — leaving it as found"
else
  pve_ssh "ip addr add ${BRIDGE_ADDR} dev ${BRIDGE}" \
    || die "could not add ${BRIDGE_ADDR} to ${BRIDGE} on ${PVE_HOST}"
  BRIDGE_ADDED=1
fi

if [[ -n "${LIST}" ]]; then
  guest_ssh 'sudo docker ps -a --format "table {{.Names}}\t{{.Status}}"'
  exit 0
fi

DOCKER_CMD=(sudo docker logs --tail "${TAIL}")
[[ -n "${FOLLOW}" ]] && DOCKER_CMD+=(--follow)
DOCKER_CMD+=("${CONTAINER}" "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}")

log "${TARGET} (${GUEST_IP}) :: ${CONTAINER}"

if [[ -n "${RAW}" ]]; then
  guest_ssh "${DOCKER_CMD[*]} 2>&1"
  exit 0
fi

# gunicorn's own startup lines are plain text, not JSON; grep '^{' keeps jq fed
# with parseable input and drops them. jq -R//fromjson? tolerates any stray
# non-JSON that slips through rather than aborting the stream.
# Caddy logs lowercase levels, the backend uppercase; compare case-insensitively.
JQ_FILTER='select(type == "object")'
[[ -n "${ERRORS_ONLY}" ]] && JQ_FILTER+=' | select((.level // "" | ascii_upcase) as $l | $l == "ERROR" or $l == "CRITICAL" or $l == "FATAL")'
[[ -n "${REQUEST_ID}" ]] && JQ_FILTER+=" | select(.request_id == \"${REQUEST_ID}\")"

# Exception text is summarised to its final line — the actual error — with the
# full traceback a --raw run away.
#
# Two schemas share this pipeline: the backend's (timestamp/message, ISO string)
# and Caddy's (ts/msg, epoch float). Coalescing both here keeps one code path;
# Caddy's request context is flattened onto the end since that is the useful part
# of a proxy error.
JQ_FILTER+='
  | [ (if .timestamp then .timestamp
       elif .ts then (.ts | todate)
       else "-" end)
    , (.level // "-" | ascii_upcase)
    , (.logger // "-")
    , (.message // .msg // "-")
    , (if .request.method then "\(.request.method) \(.request.uri)" else empty end)
    , (if .status then "-> \(.status)" else empty end)
    , (if .duration_ms then "(\(.duration_ms)ms)" else empty end)
    , (if .exception then "\n    ↳ " + (.exception | split("\n") | map(select(length > 0)) | last) else empty end)
    ] | join(" | ")'

# Not every service logs JSON — the registry (distribution) emits logfmt, and
# gunicorn's startup banner is plain text. Rather than carry a parser per format,
# drop non-JSON here and say so if that left nothing, so an empty screen is never
# mistaken for an idle service.
matched=0
while IFS= read -r line; do
  matched=1
  printf '%s\n' "${line}"
done < <(guest_ssh "${DOCKER_CMD[*]} 2>&1" \
  | grep --line-buffered '^{' \
  | jq -Rr --unbuffered "fromjson? | ${JQ_FILTER}")

if [[ "${matched}" -eq 0 ]]; then
  if [[ -n "${ERRORS_ONLY}" || -n "${REQUEST_ID}" ]]; then
    log "no records matched — widen with -n, or drop the filter"
  else
    log "${CONTAINER} does not log JSON (or logged nothing) — use --raw to read it"
  fi
fi
