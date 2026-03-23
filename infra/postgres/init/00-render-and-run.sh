#!/usr/bin/env sh
set -eu

TEMPLATE_DIR="/docker-entrypoint-initdb.d/templates"
RENDER_DIR="/tmp/flowform-init"

require_var() {
  var_name="$1"
  eval "var_value=\${$var_name:-}"
  if [ -z "$var_value" ]; then
    echo "ERROR: required environment variable '$var_name' is not set or is empty." >&2
    exit 1
  fi
}

echo "Validating required environment variables..."

require_var POSTGRES_USER
require_var POSTGRES_DB

require_var FLOWFORM_CORE_DB
require_var FLOWFORM_RESPONSE_DB

require_var FLOWFORM_CORE_APP_USER
require_var FLOWFORM_CORE_APP_PASSWORD

require_var FLOWFORM_RESPONSE_APP_USER
require_var FLOWFORM_RESPONSE_APP_PASSWORD

require_var FLOWFORM_CORE_SCHEMA_FILE
require_var FLOWFORM_RESPONSE_SCHEMA_FILE

mkdir -p "$RENDER_DIR"

if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "ERROR: template directory not found: $TEMPLATE_DIR" >&2
  exit 1
fi

if [ ! -f "$FLOWFORM_CORE_SCHEMA_FILE" ]; then
  echo "ERROR: core schema file not found: $FLOWFORM_CORE_SCHEMA_FILE" >&2
  exit 1
fi

if [ ! -f "$FLOWFORM_RESPONSE_SCHEMA_FILE" ]; then
  echo "ERROR: response schema file not found: $FLOWFORM_RESPONSE_SCHEMA_FILE" >&2
  exit 1
fi

render() {
  infile="$1"
  outfile="$2"

  if [ ! -f "$infile" ]; then
    echo "ERROR: template file not found: $infile" >&2
    exit 1
  fi

  sed \
    -e "s|\${FLOWFORM_CORE_DB}|$FLOWFORM_CORE_DB|g" \
    -e "s|\${FLOWFORM_RESPONSE_DB}|$FLOWFORM_RESPONSE_DB|g" \
    -e "s|\${FLOWFORM_CORE_APP_USER}|$FLOWFORM_CORE_APP_USER|g" \
    -e "s|\${FLOWFORM_CORE_APP_PASSWORD}|$FLOWFORM_CORE_APP_PASSWORD|g" \
    -e "s|\${FLOWFORM_RESPONSE_APP_USER}|$FLOWFORM_RESPONSE_APP_USER|g" \
    -e "s|\${FLOWFORM_RESPONSE_APP_PASSWORD}|$FLOWFORM_RESPONSE_APP_PASSWORD|g" \
    -e "s|\${FLOWFORM_CORE_SCHEMA_FILE}|$FLOWFORM_CORE_SCHEMA_FILE|g" \
    -e "s|\${FLOWFORM_RESPONSE_SCHEMA_FILE}|$FLOWFORM_RESPONSE_SCHEMA_FILE|g" \
    "$infile" > "$outfile"
}

echo "Rendering SQL templates..."

for file in \
  00-databases.sql \
  01-roles.sql \
  02-core-schema.sql \
  03-response-schema.sql \
  04-permissions.sql
do
  render "$TEMPLATE_DIR/$file" "$RENDER_DIR/$file"
done

echo "Rendered files:"
ls -1 "$RENDER_DIR"

echo "----- BEGIN 00-databases.sql -----"
cat "$RENDER_DIR/00-databases.sql"
echo "----- END 00-databases.sql -----"

echo "----- BEGIN 01-roles.sql (masked) -----"
sed \
  -e "s|$FLOWFORM_CORE_APP_PASSWORD|****|g" \
  -e "s|$FLOWFORM_RESPONSE_APP_PASSWORD|****|g" \
  "$RENDER_DIR/01-roles.sql"
echo "----- END 01-roles.sql (masked) -----"

echo "----- BEGIN 02-core-schema.sql -----"
cat "$RENDER_DIR/02-core-schema.sql"
echo "----- END 02-core-schema.sql -----"

echo "----- BEGIN 03-response-schema.sql -----"
cat "$RENDER_DIR/03-response-schema.sql"
echo "----- END 03-response-schema.sql -----"

echo "----- BEGIN 04-permissions.sql -----"
cat "$RENDER_DIR/04-permissions.sql"
echo "----- END 04-permissions.sql -----"

echo "Running rendered SQL..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$RENDER_DIR/00-databases.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$RENDER_DIR/01-roles.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$RENDER_DIR/02-core-schema.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$RENDER_DIR/03-response-schema.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$RENDER_DIR/04-permissions.sql"

echo "Flowform bootstrap complete."