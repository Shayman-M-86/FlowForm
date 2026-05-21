"""Shared request-schema limits for API validation and OpenAPI output."""

SLUG_MAX = 80
AUTH0_USER_ID_MAX = 255

# Upper bound for numeric resource identifiers in URL paths. Matches the
# PostgreSQL ``INTEGER`` ceiling. Anything larger can't physically exist
# in any of our serial columns; reject at the routing layer instead of
# parsing into a bigint and missing the DB lookup.
INT_ID_MAX = 2**31 - 1
# Resource ids are always positive — Postgres ``SERIAL`` starts at 1.
INT_ID_MIN = 1

PROJECT_NAME_MAX = 100
SURVEY_TITLE_MAX = 200
PUBLIC_LINK_NAME_MAX = 120
TOKEN_PREFIX_MAX = 32
EMAIL_MAX = 254
TOKEN_MAX = 256
URL_MAX = 2048
ID_TOKEN_MAX = 8192

ERROR_CODE_MAX = 128
ERROR_MESSAGE_MAX = 1000
ISO_DATETIME_MAX = 35
UUID_STRING_MAX = 36

SCHEMA_ID_MAX = 128
QUESTION_TITLE_MAX = 500
QUESTION_LABEL_MAX = 5000
CHOICE_OPTION_LABEL_MAX = 1000
MATCHING_ITEM_LABEL_MAX = 250
RATING_LABEL_MAX = 50
FIELD_PLACEHOLDER_MAX = 50
ANSWER_TEXT_MAX = 5000
DATE_VALUE_MAX = 10

QUESTION_ITEMS_MAX = 10
CHOICE_OPTION_LABELS_TOTAL_MAX = 4000
MATCHING_ITEMS_TOTAL_LABEL_MAX = 2000
NODE_CONTENT_BYTES_MAX = 10_000
