#!/usr/bin/env bash
# `rehearsal rotate app|database|linkage` — rotate one managed secret family,
# sync it to LocalStack, and reconverge every consumer before reporting success.
# App/database rotation is rolled back on sync or convergence failure. Linkage
# rotation is append-only: once synced, a failed app restart leaves the new
# version retained and reports the recovery command instead of rewriting history.

_cmd_rotate_cleanup_exit() {
  local status=$?
  trap - EXIT INT TERM HUP
  secrets_cleanup_resources
  exit "${status}"
}

_cmd_rotate_cleanup_signal() {
  trap - EXIT INT TERM HUP
  secrets_cleanup_resources
  exit 130
}

_rotate_converge() {
  local target="$1"
  case "${target}" in
    app|linkage)
      rehearsal_converge app
      ;;
    database)
      # The DB bootstrap observes the changed password fingerprint, deliberately
      # recreates its tmpfs-backed cluster, then verifies both roles. Restart the
      # app afterward so its secret mounts and connection pool use the new values.
      rehearsal_converge db && rehearsal_converge app
      ;;
  esac
}

_rotate_rollback_plain() {
  local target="$1"
  log "rotation failed; restoring the previous ${target} bundle values"
  secrets_restore_rotation "${target}" || {
    log "ERROR: could not restore the PVE-host bundle from ${ROTATION_BACKUP_DIR}"
    return 1
  }
  secrets_stream_archive || {
    log "ERROR: bundle restored, but LocalStack rollback synchronisation failed"
    return 1
  }
  _rotate_converge "${target}" || {
    log "ERROR: bundle and LocalStack restored, but consumer rollback convergence failed"
    return 1
  }
  return 0
}

cmd_rotate_main() {
  local target="${1:-}"
  case "${target}" in
    app|database|linkage) ;;
    -h|--help|"")
      printf '%s\n' 'Usage: rehearsal rotate <app|database|linkage>' \
        'Rotate one managed secret family, sync it, and reconverge its consumers.'
      [[ -n "${target}" ]] && return 0
      return 2
      ;;
    *) die "unknown rotation target: ${target} (expected app, database, or linkage)" ;;
  esac
  [[ $# -eq 1 ]] || die "rotate accepts exactly one target"

  # shellcheck source=rehearsal-secrets.sh
  source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/rehearsal-secrets.sh"
  trap _cmd_rotate_cleanup_exit EXIT
  trap _cmd_rotate_cleanup_signal INT TERM HUP

  secrets_preflight
  secrets_make_work_dir
  secrets_ensure_bundle || die "failed to ensure the persistent secret bundle on the PVE host"
  secrets_resolve_external
  secrets_prepare_bridge

  log "rotating ${target} secret material in the persistent PVE-host bundle"
  secrets_begin_rotation "${target}" || die "could not create and atomically install the ${target} rotation candidate"

  if ! secrets_stream_archive; then
    if [[ "${target}" == "linkage" ]]; then
      secrets_finish_rotation || true
      die "linkage sync failed; the append-only candidate remains in the bundle so history is not rewritten (rerun: rehearsal sync)"
    fi
    _rotate_rollback_plain "${target}" || true
    secrets_finish_rotation || true
    die "${target} rotation failed during synchronisation and rollback was attempted"
  fi

  if ! _rotate_converge "${target}"; then
    if [[ "${target}" == "linkage" ]]; then
      secrets_finish_rotation || true
      die "linkage version was synced but app convergence failed; the version is retained (recover with: rehearsal build)"
    fi
    _rotate_rollback_plain "${target}" || true
    secrets_finish_rotation || true
    die "${target} rotation failed during consumer convergence and rollback was attempted"
  fi

  secrets_finish_rotation || die "rotation succeeded, but the protected backup could not be removed: ${ROTATION_BACKUP_DIR}"
  log "${target} secret rotation completed and consumers converged"
}
