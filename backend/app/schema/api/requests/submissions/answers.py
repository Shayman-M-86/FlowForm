from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schema.api import limits
from app.schema.api.enums import ChoiceFamily, FieldFamily, MatchingFamily, RatingFamily

# =============================================================================
# Constrained String Types
# =============================================================================

SchemaIdStr = Annotated[str, Field(max_length=limits.SCHEMA_ID_MAX)]
AnswerTextValue = Annotated[str, Field(max_length=limits.ANSWER_TEXT_MAX)]


# =============================================================================
# Answer Value Models
# =============================================================================


class ChoiceAnswerValue(BaseModel):
    """Answer value for choice-based questions, containing a list of selected option IDs."""

    model_config = ConfigDict(extra="forbid")

    selected: list[SchemaIdStr] = Field(max_length=limits.ANSWER_LIST_ITEMS_MAX)

    @field_validator("selected")
    @classmethod
    def validate_selected(cls, value: list[SchemaIdStr]) -> list[SchemaIdStr]:
        if not value:
            raise ValueError("selected must contain at least one option id")
        if any(not item.strip() for item in value):
            raise ValueError("selected cannot contain empty option ids")
        return value


class FieldAnswerValue(BaseModel):
    """Answer value for open-ended questions, containing a free-form response."""

    model_config = ConfigDict(extra="forbid")

    value: AnswerTextValue | int | float | bool | date | None


class MatchPair(BaseModel):
    """A single pair of matched items for matching questions."""

    model_config = ConfigDict(extra="forbid")

    left_id: SchemaIdStr
    right_id: SchemaIdStr


class MatchingAnswerValue(BaseModel):
    """Answer value for matching questions, containing a list of matched pairs."""

    model_config = ConfigDict(extra="forbid")

    matches: list[MatchPair] = Field(max_length=limits.ANSWER_LIST_ITEMS_MAX)


class RatingAnswerValue(BaseModel):
    """Answer value for rating questions, containing a numeric rating."""

    model_config = ConfigDict(extra="forbid")

    value: int | float


# =============================================================================
# Incoming Answer Models
# =============================================================================


class ChoiceAnswerIn(BaseModel):
    """A single answer payload for a choice-based question within a submission."""

    model_config = ConfigDict(extra="forbid")

    question_key: SchemaIdStr
    answer_family: ChoiceFamily
    answer_value: ChoiceAnswerValue


class FieldAnswerIn(BaseModel):
    """A single answer payload for an open-ended question within a submission."""

    model_config = ConfigDict(extra="forbid")

    question_key: SchemaIdStr
    answer_family: FieldFamily
    answer_value: FieldAnswerValue


class MatchingAnswerIn(BaseModel):
    """A single answer payload for a matching question within a submission."""

    model_config = ConfigDict(extra="forbid")

    question_key: SchemaIdStr
    answer_family: MatchingFamily
    answer_value: MatchingAnswerValue


class RatingAnswerIn(BaseModel):
    """A single answer payload for a rating question within a submission."""

    model_config = ConfigDict(extra="forbid")

    question_key: SchemaIdStr
    answer_family: RatingFamily
    answer_value: RatingAnswerValue


AnswerIn = Annotated[
    ChoiceAnswerIn | FieldAnswerIn | MatchingAnswerIn | RatingAnswerIn,
    Field(discriminator="answer_family"),
]
