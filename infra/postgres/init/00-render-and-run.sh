#!/usr/bin/env sh
set -eu

INIT_DIR="/docker-entrypoint-initdb.d"
TEMPLATE_DIR="${INIT_DIR}/templates"
RENDER_DIR="/tmp/flowform-init"
DB_TARGET="${FF_PGDB_INIT__TARGET:-all}"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

get_var() {
  var_name="$1"
  eval "printf '%s' \"\${$var_name-}\""
}

require_var() {
  var_name="$1"
  var_value="$(get_var "$var_name")"
  [ -n "$var_value" ] || fail "required environment variable '$var_name' is not set or is empty."
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
  [ -f "$file_path" ] || fail "secret file not found: $file_path"
  tr -d '\r\n' < "$file_path"
}

read_value() {
  var_name="$1"
  file_var_name="${var_name}_FILE"

  file_path="$(get_var "$file_var_name")"
  if [ -n "$file_path" ]; then
    read_secret_file "$file_path"
    return
  fi

  var_value="$(get_var "$var_name")"
  if [ -n "$var_value" ]; then
    printf '%s\n' "$var_value"
    return
  fi

  fail "required environment variable '$var_name' or '$file_var_name' is not set."
}

list_template_vars() {
  infile="$1"

  awk '
    {
      line = $0
      while (match(line, /\$\{[A-Za-z_][A-Za-z0-9_]*\}/)) {
        var = substr(line, RSTART + 2, RLENGTH - 3)
        print var
        line = substr(line, RSTART + RLENGTH)
      }
    }
  ' "$infile" | sort -u
}

load_template_vars() {
  infile="$1"

  for var_name in $(list_template_vars "$infile"); do
    value="$(read_value "$var_name")"

    case "$var_name" in
      *__SCHEMA_FILE)
        value="$(resolve_init_path "$value")"
        [ -f "$value" ] || fail "schema file not found: $value"
        ;;
    esac

    export "$var_name=$value"
  done
}

render_template() {
  infile="$1"
  outfile="$2"

  [ -f "$infile" ] || fail "template file not found: $infile"

  load_template_vars "$infile"

  awk '
    {
      line = $0
      while (match(line, /\$\{[A-Za-z_][A-Za-z0-9_]*\}/)) {
        token = substr(line, RSTART, RLENGTH)
        var   = substr(line, RSTART + 2, RLENGTH - 3)
        value = ENVIRON[var]
        line  = substr(line, 1, RSTART - 1) value substr(line, RSTART + RLENGTH)
      }
      print line
    }
  ' "$infile" > "$outfile"
}

rendered_files=""

render_target_file() {
  source_file="$1"
  output_file="$2"

  render_template "$TEMPLATE_DIR/$source_file" "$RENDER_DIR/$output_file"
  rendered_files="${rendered_files}${rendered_files:+ }$output_file"
}

echo "Validating bootstrap inputs..."

require_var POSTGRES_USER
require_var POSTGRES_DB

[ -d "$TEMPLATE_DIR" ] || fail "template directory not found: $TEMPLATE_DIR"
mkdir -p "$RENDER_DIR"

echo "Rendering SQL templates for target: $DB_TARGET"

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
  *)
    fail "FF_PGDB_INIT__TARGET must be one of: core, response, all."
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
  psql -v ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    -f "$RENDER_DIR/$file"
done

echo "Flowform bootstrap complete."