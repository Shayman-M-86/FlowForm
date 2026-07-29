#!/bin/sh
set -eu

: "${FLOWFORM_ALLOY_ROLE:?set FLOWFORM_ALLOY_ROLE to app or proxy}"

case "${FLOWFORM_ALLOY_ROLE}" in
  app|proxy)
    config="/etc/flowform/alloy/${FLOWFORM_ALLOY_ROLE}.alloy"
    ;;
  *)
    printf 'invalid FLOWFORM_ALLOY_ROLE: %s (expected app or proxy)\n' \
      "${FLOWFORM_ALLOY_ROLE}" >&2
    exit 64
    ;;
esac

if [ "${1:-}" = "validate" ]; then
  exec /bin/alloy validate "${config}"
fi

if [ "$#" -gt 0 ]; then
  exec /bin/alloy "$@"
fi

exec /bin/alloy run \
  --server.http.listen-addr=127.0.0.1:12345 \
  --storage.path=/var/lib/alloy/data \
  "${config}"
