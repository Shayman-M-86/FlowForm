#!/usr/bin/env sh
set -eu

INIT_DIR="/docker-entrypoint-initdb.d"
TEMPLATE_DIR="/docker-entrypoint-initdb.d/templates"
RENDER_DIR="/tmp/flowform-init"
DB_TARGET="${FF_PGDB_INIT__TARGET:-all}"

require_var() {
  var_name="$1"
  eval "var_value=\${$var_name:-}"
  if [ -z "$var_value" ]; then
    echo "ERROR: required environment variable '$var_name' is not set or is empty." >&2
    exit 1
  fi
}

resolve_init_path() {
  input_path="$1"

  case "$input_path" in
    /*)
      printf '%s\n' "$input_path"
      ;;
    *)
      printf '%s/%s\n' "$INIT_DIR" "$input_path"
      ;;
  esac
}

read_secret_file() {
  file_path="$1"

  if [ ! -f "$file_path" ]; then
    echo "ERROR: secret file not found: $file_path" >&2
    exit 1
  fi

  tr -d '\r\n' < "$file_path"
}

read_value() {
  var_name="$1"
  file_var_name="${var_name}_FILE"

  eval "file_path=\${$file_var_name:-}"
  if [ -n "$file_path" ]; then
    read_secret_file "$file_path"
    return
  fi

  eval "var_value=\${$var_name:-}"
  if [ -n "$var_value" ]; then
    printf '%s\n' "$var_value"
    return
  fi

  echo "ERROR: required environment variable '$var_name' or '$file_var_name' is not set." >&2
  exit 1
}

validate_core_inputs() {
  require_var FF_PGDB_CORE__DB_NAME
  require_var FF_PGDB_CORE__APP_USER
  require_var FF_PGDB_CORE__SCHEMA_FILE
}

validate_response_inputs() {
  require_var FF_PGDB_RESPONSE__DB_NAME
  require_var FF_PGDB_RESPONSE__APP_USER
  require_var FF_PGDB_RESPONSE__SCHEMA_FILE
}

echo "Validating required environment variables..."

require_var POSTGRES_USER
require_var POSTGRES_DB

case "$DB_TARGET" in
  core)
    validate_core_inputs
    FF_PGDB_CORE__SCHEMA_FILE="$(resolve_init_path "$FF_PGDB_CORE__SCHEMA_FILE")"
    FF_PGDB_CORE__APP_PASSWORD="$(read_value FF_PGDB_CORE__APP_PASSWORD)"
    ;;
  response)
    validate_response_inputs
    FF_PGDB_RESPONSE__SCHEMA_FILE="$(resolve_init_path "$FF_PGDB_RESPONSE__SCHEMA_FILE")"
    FF_PGDB_RESPONSE__APP_PASSWORD="$(read_value FF_PGDB_RESPONSE__APP_PASSWORD)"
    ;;
  all)
    validate_core_inputs
    validate_response_inputs
    FF_PGDB_CORE__SCHEMA_FILE="$(resolve_init_path "$FF_PGDB_CORE__SCHEMA_FILE")"
    FF_PGDB_RESPONSE__SCHEMA_FILE="$(resolve_init_path "$FF_PGDB_RESPONSE__SCHEMA_FILE")"
    FF_PGDB_CORE__APP_PASSWORD="$(read_value FF_PGDB_CORE__APP_PASSWORD)"
    FF_PGDB_RESPONSE__APP_PASSWORD="$(read_value FF_PGDB_RESPONSE__APP_PASSWORD)"
    ;;
  *)
    echo "ERROR: FF_PGDB_INIT__TARGET must be one of: core, response, all." >&2
    exit 1
    ;;
esac

mkdir -p "$RENDER_DIR"

if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "ERROR: template directory not found: $TEMPLATE_DIR" >&2
  exit 1
fi

if [ "$DB_TARGET" = "core" ] || [ "$DB_TARGET" = "all" ]; then
  if [ ! -f "$FF_PGDB_CORE__SCHEMA_FILE" ]; then
    echo "ERROR: core schema file not found: $FF_PGDB_CORE__SCHEMA_FILE" >&2
    exit 1
  fi
fi

if [ "$DB_TARGET" = "response" ] || [ "$DB_TARGET" = "all" ]; then
  if [ ! -f "$FF_PGDB_RESPONSE__SCHEMA_FILE" ]; then
    echo "ERROR: response schema file not found: $FF_PGDB_RESPONSE__SCHEMA_FILE" >&2
    exit 1
  fi
fi

render() {
  infile="$1"
  outfile="$2"

  if [ ! -f "$infile" ]; then
    echo "ERROR: template file not found: $infile" >&2
    exit 1
  fi

  sed \
    -e "s|\${FF_PGDB_CORE__DB_NAME}|${FF_PGDB_CORE__DB_NAME:-}|g" \
    -e "s|\${FF_PGDB_RESPONSE__DB_NAME}|${FF_PGDB_RESPONSE__DB_NAME:-}|g" \
    -e "s|\${FF_PGDB_CORE__APP_USER}|${FF_PGDB_CORE__APP_USER:-}|g" \
    -e "s|\${FF_PGDB_CORE__APP_PASSWORD}|${FF_PGDB_CORE__APP_PASSWORD:-}|g" \
    -e "s|\${FF_PGDB_RESPONSE__APP_USER}|${FF_PGDB_RESPONSE__APP_USER:-}|g" \
    -e "s|\${FF_PGDB_RESPONSE__APP_PASSWORD}|${FF_PGDB_RESPONSE__APP_PASSWORD:-}|g" \
    -e "s|\${FF_PGDB_CORE__SCHEMA_FILE}|${FF_PGDB_CORE__SCHEMA_FILE:-}|g" \
    -e "s|\${FF_PGDB_RESPONSE__SCHEMA_FILE}|${FF_PGDB_RESPONSE__SCHEMA_FILE:-}|g" \
    "$infile" > "$outfile"
}

echo "Rendering SQL templates..."

rendered_files=""

render_target_file() {
  source_file="$1"
  output_file="$2"
  render "$TEMPLATE_DIR/$source_file" "$RENDER_DIR/$output_file"
  rendered_files="$rendered_files $output_file"
}

case "$DB_TARGET" in
  core)
    render_target_file "core/01-create-role.sql" "01-create-role.sql"
    render_target_file "core/02-create-schema.sql" "02-create-schema.sql"
    render_target_file "core/03-grant-permissions.sql" "03-grant-permissions.sql"
    ;;
  response)
    render_target_file "response/01-create-role.sql" "01-create-role.sql"
    render_target_file "response/02-create-schema.sql" "02-create-schema.sql"
    render_target_file "response/03-grant-permissions.sql" "03-grant-permissions.sql"
    ;;
  all)
    render_target_file "shared/00-create-databases.sql" "00-create-databases.sql"
    render_target_file "shared/01-create-roles.sql" "01-create-roles.sql"
    render_target_file "core/02-create-schema.sql" "02-create-core-schema.sql"
    render_target_file "response/02-create-schema.sql" "03-create-response-schema.sql"
    render_target_file "core/03-grant-permissions.sql" "04-grant-core-permissions.sql"
    render_target_file "response/03-grant-permissions.sql" "05-grant-response-permissions.sql"
    ;;
esac

echo "Rendered files:"
ls -1 "$RENDER_DIR"

for file in $rendered_files
do
  echo "----- BEGIN $file -----"
  case "$file" in
    01-create-roles.sql|01-create-role.sql)
      echo "Role SQL rendered successfully (content suppressed because it contains credentials)."
      ;;
    *)
      cat "$RENDER_DIR/$file"
      ;;
  esac
  echo "----- END $file -----"
done

echo "Running rendered SQL..."

for file in $rendered_files
do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$RENDER_DIR/$file"
done

echo "Flowform bootstrap complete."
