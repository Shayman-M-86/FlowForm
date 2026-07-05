"""Shared request-schema limits for API validation and OpenAPI output."""

from app.domain.permissions import PERMISSIONS

# Generic string and token limits.
# These are reused across multiple request/response schemas.
SLUG_MAX = 80
AUTH0_USER_ID_MAX = 255
EMAIL_MAX = 254
TOKEN_MAX = 256
URL_MAX = 2048
ID_TOKEN_MAX = 8192
CONTENT_ID_MAX = 32767


# Integer ID limits. Match PostgreSQL INTEGER-backed positive resource IDs.
INT_ID_MAX = 2**31 - 1
INT_ID_MIN = 1


# Project, membership, role, and invitation limits.
PROJECT_NAME_MAX = 100
PROJECT_MEMBER_STATUS_MAX = 9
PROJECT_INVITATION_STATUS_MAX = 8
PROJECT_ROLE_NAME_MAX = 80
PROJECT_ROLE_DESCRIPTION_MAX = 500
PROJECT_ROLE_PERMISSION_NAME_MAX = 64
# One project role cannot grant more permissions than the platform defines.
PROJECT_ROLE_PERMISSIONS_MAX = len(PERMISSIONS.all())
# One survey role can only grant survey-scoped permissions.
SURVEY_ROLE_PERMISSIONS_MAX = len(PERMISSIONS.survey.values()) + len(PERMISSIONS.submission.values())
INVITE_MESSAGE_MAX = 500


# Survey and public-link limits.
SURVEY_TITLE_MAX = 200
PUBLIC_LINK_NAME_MAX = 120

# Matches ck_project_subjects_subject_code_len (1-128, trimmed).
SUBJECT_CODE_MAX = 128


# Standard API error and serialized scalar limits.
ERROR_CODE_MAX = 128
ERROR_MESSAGE_MAX = 1000
ISO_DATETIME_MAX = 35
UUID_STRING_MAX = 36


# Survey content schema string limits.
SCHEMA_ID_MAX = 128
QUESTION_TITLE_MAX = 500
QUESTION_LABEL_MAX = 1000
CHOICE_OPTION_LABEL_MAX = 1000
MATCHING_ITEM_LABEL_MAX = 250
RATING_LABEL_MAX = 50
FIELD_PLACEHOLDER_MAX = 50
ANSWER_TEXT_MAX = 1000
ANSWER_LIST_ITEMS_MAX = 50
SUBMISSION_METADATA_ITEMS_MAX = 50
DATE_VALUE_MAX = 10


# Standard list pagination limits.
LIST_PAGE_DEFAULT = 1
LIST_PAGE_MIN = 1
LIST_PAGE_SIZE_DEFAULT = 20
LIST_PAGE_SIZE_MIN = 1
LIST_PAGE_SIZE_MAX = 100


# Survey content collection and serialized-size limits.
QUESTION_ITEMS_MAX = 10
RULE_ITEMS_MAX = 50
SCORING_RULE_ITEMS_MAX = 50
CHOICE_OPTION_LABELS_TOTAL_MAX = 3000
MATCHING_ITEMS_TOTAL_LABEL_MAX = 2000
NODE_CONTENT_BYTES_MAX = 10_000


# Survey content numeric bounds.
CONTENT_SORT_KEY_MIN_EXCLUSIVE = 0
RATING_RANGE_MIN = -1000
RATING_RANGE_MAX = 1000
CHOICE_MIN_SELECTED_MIN = 0
CHOICE_MAX_SELECTED_MIN = 1
RATING_STEP_MIN_EXCLUSIVE = 0
RATING_STARS_MIN = 1
RATING_STARS_MAX = 12


# Answer value numeric bounds.
ANSWER_NUMBER_MIN = -1_000_000
ANSWER_NUMBER_MAX = 1_000_000
PHONE_MAX = 64
