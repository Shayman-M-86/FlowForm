"""Shared resource ceilings and pagination configuration.

Domain-specific constraints live once in their named value types. These
constants are shared categories, configuration defaults, or storage boundaries.
"""

DEFAULT_STRING_MAX = 2_000
SHORT_STRING_MAX = 128
LONG_STRING_MAX = 10_000
DEFAULT_COLLECTION_MAX = 100
SURVEY_BLOCKS_MAX = 1_000

# Shared by slug validation and the URL converter.
SLUG_MAX = 80

# PostgreSQL BIGINT identity range; positive minimums are explicit in the types.
BIGINT_ID_MAX = 2**63 - 1

LIST_PAGE_DEFAULT = 1
LIST_PAGE_SIZE_DEFAULT = 20
LIST_PAGE_SIZE_MAX = 100
