#!/usr/bin/env bash
# `rehearsal logs` — tail container logs from a rehearsal VM on the private bridge.
#
# The backend emits structured JSON (FLOWFORM_LOGGING_LOG_JSON=true), where an
# unhandled exception is a single record carrying a multi-KB traceback. Piping
# raw output at a terminal is unreadable, so the default view flattens each
# record to one line and drops the traceback; --raw opts back into full JSON
# when you need the stack.
#
# Usage:
#   rehearsal logs [proxy|app|fixtures|db] [options] [-- <extra docker logs args>]
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
#   rehearsal logs app -f                     # tail the backend
#   rehearsal logs app -e -n 200              # recent failures only
#   rehearsal logs app -r 350889d7-7602-...   # one request end to end
#   rehearsal logs app --raw -n 5             # full tracebacks
#   rehearsal logs proxy -c flowform-proxy-squid-1 -f
#   rehearsal logs db -f                      # tail PostgreSQL on VM 240

_cmd_logs_usage() {
  sed -n '/^# Usage:/,/^[^#]/p' "${BASH_SOURCE[0]}" | grep '^#' | sed 's/^# \{0,1\}//'
}

cmd_logs_main() {
  local TARGET="app" CONTAINER="" TAIL="50" FOLLOW="" RAW="" LIST="" \
        ERRORS_ONLY="" REQUEST_ID="" EXTRA_ARGS=()

  case "${1:-}" in
    proxy|app|fixtures|registry|localstack|db) TARGET="$1"; shift ;;
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
      -h|--help)       _cmd_logs_usage; return 0 ;;
      --)              shift; EXTRA_ARGS=("$@"); break ;;
      *)               die "unknown option: $1 (try: rehearsal logs -h)" ;;
    esac
  done

  rehearsal_preflight
  command -v jq >/dev/null || [[ -n "${RAW}" ]] || die "jq not found — install it, or pass --raw"

  CONTAINER="${CONTAINER:-$(rehearsal_default_container "${TARGET}")}"
  local GUEST_IP; GUEST_IP="$(rehearsal_ip "${TARGET}")"

  # logs is interactive; a 5s connect timeout keeps a dead box from hanging.
  export PVE_SSH_CONNECT_TIMEOUT=5

  cleanup_exit() {
    local status=$?
    trap - EXIT INT TERM HUP
    rehearsal_bridge_down
    exit "${status}"
  }
  cleanup_signal() {
    trap - EXIT INT TERM HUP
    rehearsal_bridge_down
    exit 130
  }
  trap cleanup_exit EXIT
  trap cleanup_signal INT TERM HUP
  rehearsal_bridge_up

  if [[ -n "${LIST}" ]]; then
    guest_ssh "${GUEST_IP}" 'sudo docker ps -a --format "table {{.Names}}\t{{.Status}}"'
    return 0
  fi

  local DOCKER_CMD=(sudo docker logs --tail "${TAIL}")
  [[ -n "${FOLLOW}" ]] && DOCKER_CMD+=(--follow)
  DOCKER_CMD+=("${CONTAINER}" "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}")
  local DOCKER_REMOTE
  printf -v DOCKER_REMOTE '%q ' "${DOCKER_CMD[@]}"

  log "${TARGET} (${GUEST_IP}) :: ${CONTAINER}"

  if [[ -n "${RAW}" ]]; then
    guest_ssh "${GUEST_IP}" "${DOCKER_REMOTE} 2>&1"
    return 0
  fi

  # gunicorn's own startup lines are plain text, not JSON; grep '^{' keeps jq fed
  # with parseable input and drops them. fromjson? tolerates any stray non-JSON
  # that slips through rather than aborting the stream.
  # Caddy logs lowercase levels, the backend uppercase; compare case-insensitively.
  local JQ_FILTER='select(type == "object")'
  [[ -n "${ERRORS_ONLY}" ]] && JQ_FILTER+=' | select((.level // "" | ascii_upcase) as $l | $l == "ERROR" or $l == "CRITICAL" or $l == "FATAL")'
  [[ -n "${REQUEST_ID}" ]] && JQ_FILTER+=' | select(.request_id == $request_id)'

  # Exception text is summarised to its final line — the actual error — with the
  # full traceback a --raw run away. Two schemas share this pipeline: the
  # backend's (timestamp/message, ISO string) and Caddy's (ts/msg, epoch float).
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

  # Not every service logs JSON — the registry emits logfmt, gunicorn's banner is
  # plain text. Drop non-JSON here and say so if that left nothing, so an empty
  # screen is never mistaken for an idle service.
  local matched=0 line
  while IFS= read -r line; do
    matched=1
    printf '%s\n' "${line}"
  done < <(guest_ssh "${GUEST_IP}" "${DOCKER_REMOTE} 2>&1" \
    | grep --line-buffered '^{' \
    | jq -Rr --unbuffered --arg request_id "${REQUEST_ID}" "fromjson? | ${JQ_FILTER}")

  if [[ "${matched}" -eq 0 ]]; then
    if [[ -n "${ERRORS_ONLY}" || -n "${REQUEST_ID}" ]]; then
      log "no records matched — widen with -n, or drop the filter"
    else
      log "${CONTAINER} does not log JSON (or logged nothing) — use --raw to read it"
    fi
  fi
}
