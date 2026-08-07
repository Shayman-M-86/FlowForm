"""The compact publication issue contract and its stable codes."""

from dataclasses import dataclass
from typing import Final, Literal

PublicationIssueCode = Literal[
    "duplicate_section_id",
    "duplicate_block_id",
    "duplicate_field_id",
    "duplicate_field_key",
    "condition_field_missing",
    "condition_self_reference",
    "condition_operator_incompatible",
    "condition_value_type_invalid",
    "condition_option_missing",
    "condition_dependency_cycle",
]

DUPLICATE_SECTION_ID: Final[PublicationIssueCode] = "duplicate_section_id"
DUPLICATE_BLOCK_ID: Final[PublicationIssueCode] = "duplicate_block_id"
DUPLICATE_FIELD_ID: Final[PublicationIssueCode] = "duplicate_field_id"
DUPLICATE_FIELD_KEY: Final[PublicationIssueCode] = "duplicate_field_key"
CONDITION_FIELD_MISSING: Final[PublicationIssueCode] = "condition_field_missing"
CONDITION_SELF_REFERENCE: Final[PublicationIssueCode] = "condition_self_reference"
CONDITION_OPERATOR_INCOMPATIBLE: Final[PublicationIssueCode] = "condition_operator_incompatible"
CONDITION_VALUE_TYPE_INVALID: Final[PublicationIssueCode] = "condition_value_type_invalid"
CONDITION_OPTION_MISSING: Final[PublicationIssueCode] = "condition_option_missing"
CONDITION_DEPENDENCY_CYCLE: Final[PublicationIssueCode] = "condition_dependency_cycle"


@dataclass(frozen=True, slots=True)
class PublicationIssue:
    """One document-wide logical defect that blocks publication."""

    code: PublicationIssueCode
    message: str
    object_id: str | None = None
