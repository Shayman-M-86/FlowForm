#!/usr/bin/env bash
# generate-env-files.sh
# Reads environment variables and routes them into the appropriate env files.
#
# Usage:
#   ./scripts/generate-env-files.sh [SOURCE_FILE]

set -eu

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
echo "Script dir: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"

DOCKER_DIR="$PROJECT_ROOT/infra/docker"

BACKEND_ENV="$DOCKER_DIR/.backend.env"
DB_CORE_ENV="$DOCKER_DIR/.db.core.env"
DB_RESPONSE_ENV="$DOCKER_DIR/.db.response.env"

# ------------------------------------------------------------------
# Single source of truth:
# each variable name is declared once, here.
# These lists are used for both routing and required checks.
# ------------------------------------------------------------------
BACKEND_VARS="
FLOWFORM_ENV


FLOWFORM_AUTH0_DOMAIN
FLOWFORM_AUTH0_AUDIENCE
"

DB_CORE_VARS="
DATABASE_CORE_HOST
DATABASE_CORE_NAME
DATABASE_CORE_APP_USER
DATABASE_CORE_SCHEMA_FILE
"

DB_RESPONSE_VARS="
DATABASE_RESPONSE_HOST
DATABASE_RESPONSE_NAME
DATABASE_RESPONSE_APP_USER
DATABASE_RESPONSE_SCHEMA_FILE
"

# ------------------------------------------------------------------
# Input source: file arg or current environment
# ------------------------------------------------------------------
if [ $# -ge 1 ]; then
  SOURCE_FILE="$1"
  [ -f "$SOURCE_FILE" ] || {
    printf 'ERROR: file not found: %s\n' "$SOURCE_FILE" >&2
    exit 1
  }

  input() {
    grep -v '^[[:space:]]*#' "$SOURCE_FILE" | grep -v '^[[:space:]]*$'
  }
else
  input() {
    env | sort
  }
fi

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
contains_word() {
  list="$1"
  word="$2"

for item in $list; do
    [ "$item" = "$word" ] && return 0
  done

  return 1
}

append_seen() {
  seen_list="$1"
  key="$2"

  if contains_word "$seen_list" "$key"; then
    printf '%s' "$seen_list"
  else
    if [ -n "$seen_list" ]; then
      printf '%s\n%s' "$seen_list" "$key"
    else
      printf '%s' "$key"
    fi
  fi
}

check_required_list() {
  required_list="$1"
  seen_list="$2"
  label="$3"

  missing_any=0

  for var in $required_list; do
    if ! contains_word "$seen_list" "$var"; then
      printf 'ERROR: missing required %s variable: %s\n' "$label" "$var" >&2
      missing_any=1
    fi
  done

  return "$missing_any"
}

# ------------------------------------------------------------------
# Temp files so real files are not touched unless validation succeeds
# ------------------------------------------------------------------
BACKEND_TMP="$(mktemp "$DOCKER_DIR/.backend.env.tmp.XXXXXX")"
DB_CORE_TMP="$(mktemp "$DOCKER_DIR/.db.core.env.tmp.XXXXXX")"
DB_RESPONSE_TMP="$(mktemp "$DOCKER_DIR/.db.response.env.tmp.XXXXXX")"

cleanup() {
  rm -f "$BACKEND_TMP" "$DB_CORE_TMP" "$DB_RESPONSE_TMP"
}
trap cleanup EXIT INT TERM

: > "$BACKEND_TMP"
: > "$DB_CORE_TMP"
: > "$DB_RESPONSE_TMP"

backend_count=0
db_core_count=0
db_response_count=0

seen_backend=""
seen_db_core=""
seen_db_response=""

# ------------------------------------------------------------------
# Route variables into temp files
# ------------------------------------------------------------------
while IFS= read -r line; do
  key="${line%%=*}"
  rest="${line#*=}"

  [ -n "$key" ] || continue
  [ "$key" != "$line" ] || continue

  if contains_word "$BACKEND_VARS" "$key"; then
    printf '%s=%s\n' "$key" "$rest" >> "$BACKEND_TMP"
    backend_count=$((backend_count + 1))
    seen_backend="$(append_seen "$seen_backend" "$key")"
  fi

  if contains_word "$DB_CORE_VARS" "$key"; then
    printf '%s=%s\n' "$key" "$rest" >> "$DB_CORE_TMP"
    db_core_count=$((db_core_count + 1))
    seen_db_core="$(append_seen "$seen_db_core" "$key")"
  fi

  if contains_word "$DB_RESPONSE_VARS" "$key"; then
    printf '%s=%s\n' "$key" "$rest" >> "$DB_RESPONSE_TMP"
    db_response_count=$((db_response_count + 1))
    seen_db_response="$(append_seen "$seen_db_response" "$key")"
  fi
done << EOF
$(input)
EOF

# ------------------------------------------------------------------
# Validate before replacing real files
# ------------------------------------------------------------------
failed=0

if ! check_required_list "$BACKEND_VARS" "$seen_backend" "backend"; then
  failed=1
fi

if ! check_required_list "$DB_CORE_VARS" "$seen_db_core" "db core"; then
  failed=1
fi

if ! check_required_list "$DB_RESPONSE_VARS" "$seen_db_response" "db response"; then
  failed=1
fi

if [ "$backend_count" -eq 0 ]; then
  printf 'ERROR: no backend variables were written\n' >&2
  failed=1
fi

if [ "$db_core_count" -eq 0 ]; then
  printf 'ERROR: no db core variables were written\n' >&2
  failed=1
fi

if [ "$db_response_count" -eq 0 ]; then
  printf 'ERROR: no db response variables were written\n' >&2
  failed=1
fi

if [ "$failed" -ne 0 ]; then
  printf 'Aborted: env files were not updated.\n' >&2
  exit 1
fi

# ------------------------------------------------------------------
# Replace real files only after validation succeeds
# ------------------------------------------------------------------
mv "$BACKEND_TMP" "$BACKEND_ENV"
mv "$DB_CORE_TMP" "$DB_CORE_ENV"
mv "$DB_RESPONSE_TMP" "$DB_RESPONSE_ENV"

trap - EXIT INT TERM

printf 'Generated:\n'
printf '  %s (%d vars)\n' "$BACKEND_ENV" "$backend_count"
printf '  %s (%d vars)\n' "$DB_CORE_ENV" "$db_core_count"
printf '  %s (%d vars)\n' "$DB_RESPONSE_ENV" "$db_response_count"