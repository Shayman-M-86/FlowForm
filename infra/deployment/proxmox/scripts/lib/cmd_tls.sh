#!/usr/bin/env bash
# `rehearsal tls` — create or validate the ignored machine-local CA and leaves.

cmd_tls_main() {
  if [[ $# -gt 0 ]]; then
    case "${1:-}" in
      -h|--help)
        printf '%s\n' \
          'Usage: rehearsal tls' \
          '' \
          'Creates the ignored machine-local rehearsal CA on first use.' \
          'A valid existing CA is preserved; missing or invalid leaf pairs are' \
          'regenerated under it. An invalid CA pair is never overwritten.'
        return 0
        ;;
      *) die "rehearsal tls does not accept arguments (try --help)" ;;
    esac
  fi

  # shellcheck source=infra/deployment/proxmox/scripts/lib/rehearsal-tls.sh
  source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/rehearsal-tls.sh"
  rehearsal_ensure_tls
}
