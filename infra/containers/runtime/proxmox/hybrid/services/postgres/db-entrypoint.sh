#!/bin/sh
set -eu

if [ -s "$PGDATA/PG_VERSION" ] && [ ! -f "$PGDATA/.flowform-initialized" ]; then
  echo 'PostgreSQL storage lacks the FlowForm initialization marker. Inspect or restore it before starting.' >&2
  exit 1
fi

source_dir=/run/flowform-db-source
runtime_dir=/run/flowform-db
for file in server.crt server.key; do
  install -m 0600 -o postgres -g postgres "$source_dir/$file" "$runtime_dir/$file"
done
# The init SQL embeds role passwords in single-quoted literals. Require one line
# of at least 16 printable characters without quotes or backslashes, which
# covers the generated and seeded db-secrets values.
for key in DATABASE_INIT_PASSWORD DATABASE_CORE_APP_PASSWORD DATABASE_RESPONSE_APP_PASSWORD; do
  file="$source_dir/$key.secret.txt"
  if [ "$(wc -l < "$file")" -gt 1 ] ||
    ! LC_ALL=C grep -Eq '^[[:graph:]]{16,}$' "$file" ||
    LC_ALL=C grep -q "['\\\\\"]" "$file"; then
    echo "Invalid password file format: $key (expected one line of 16+ printable characters without quotes or backslashes)" >&2
    exit 1
  fi
  install -m 0600 -o postgres -g postgres "$source_dir/$key.secret.txt" "$runtime_dir/$key"
done

# The upstream entrypoint starts a Unix-socket-only server for initialization.
# Peer auth allows that bootstrap and local administration by the postgres user.
cat > "$runtime_dir/pg_hba.conf" <<EOF_HBA
local   all                 postgres                  peer
hostssl flowform_core       flowform_core_app         ${HYBRID_APP_DB_IP}/32 scram-sha-256
hostssl flowform_response   flowform_response_app     ${HYBRID_APP_DB_IP}/32 scram-sha-256
EOF_HBA
chmod 0644 "$runtime_dir/pg_hba.conf"

exec docker-entrypoint.sh "$@"
