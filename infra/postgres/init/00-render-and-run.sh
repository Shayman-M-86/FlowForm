#!/usr/bin/env sh
set -eu

TEMPLATE_DIR="/docker-entrypoint-initdb.d/templates"
RENDER_DIR="/tmp/flowform-init"

mkdir -p "$RENDER_DIR"

echo "Rendering SQL templates..."

render() {
  infile="$1"
  outfile="$2"

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

for file in \
  00-databases.sql.template \
  01-roles.sql.template \
  02-core-schema.sql.template \
  03-response-schema.sql.template \
  04-permissions.sql.template
do
  render "$TEMPLATE_DIR/$file" "$RENDER_DIR/${file%.template}"
done

echo "Running rendered SQL..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$RENDER_DIR/00-databases.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$RENDER_DIR/01-roles.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$RENDER_DIR/02-core-schema.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$RENDER_DIR/03-response-schema.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$RENDER_DIR/04-permissions.sql"

echo "Flowform bootstrap complete."