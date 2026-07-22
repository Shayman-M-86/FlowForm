#!/usr/bin/env bash
# `rehearsal sync` — reconcile the PVE-host secret bundle into the isolated
# LocalStack fixture. This is the only supported path for real secrets to enter
# the rehearsal.

_cmd_sync_cleanup_exit() {
  local status=$?
  trap - EXIT INT TERM HUP
  secrets_cleanup_resources
  exit "${status}"
}

_cmd_sync_cleanup_signal() {
  trap - EXIT INT TERM HUP
  secrets_cleanup_resources
  exit 130
}

cmd_sync_main() {
  case "${1:-}" in
    "") ;;
    -h|--help)
      printf '%s\n' 'Usage: rehearsal sync' \
        'Synchronise the persistent PVE-host secret bundle into VM 230 LocalStack.'
      return 0
      ;;
    *) die "unknown sync argument: $1" ;;
  esac

  # shellcheck source=rehearsal-secrets.sh
  source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/rehearsal-secrets.sh"
  trap _cmd_sync_cleanup_exit EXIT
  trap _cmd_sync_cleanup_signal INT TERM HUP

  secrets_preflight
  secrets_make_work_dir
  secrets_ensure_bundle || die "failed to ensure ${BUNDLE_DIR} on the PVE host; verify PVE SSH access plus root availability of openssl/jq, then rerun 'rehearsal sync'"
  secrets_resolve_external
  secrets_prepare_bridge
  secrets_stream_archive || die "secret synchronisation into VM 230 failed; review the preceding named-secret error, confirm VM 230 is healthy, then rerun 'rehearsal sync'"
  log "rehearsal secrets synchronised into LocalStack (scope=${FLOWFORM_SCOPE})"
}
