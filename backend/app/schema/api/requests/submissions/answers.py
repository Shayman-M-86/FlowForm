from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChoiceAnswerValue(BaseModel):
    """Answer value for choice-based questions, containing a list of selected option IDs."""
    model_config = ConfigDict(extra="forbid")

    selected: list[str]

    @field_validator("selected")
    @classmethod
    def validate_selected(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("selected must contain at least one option id")
        if any(not item.strip() for item in value):
            raise ValueError("selected cannot contain empty option ids")
        return value


class FieldAnswerValue(BaseModel):
    """Answer value for open-ended questions, containing a free-form response."""
    model_config = ConfigDict(extra="forbid")

    value: str | int | float | bool | date | None


class MatchPair(BaseModel):
    """A single pair of matched items for matching questions."""
    model_config = ConfigDict(extra="forbid")

    left_id: str
    right_id: str


class MatchingAnswerValue(BaseModel):
    """Answer value for matching questions, containing a list of matched pairs."""
    model_config = ConfigDict(extra="forbid")

    matches: list[MatchPair]


class RatingAnswerValue(BaseModel):
    """Answer value for rating questions, containing a numeric rating."""
    model_config = ConfigDict(extra="forbid")

    value: int | float


class ChoiceAnswerIn(BaseModel):
    """A single answer payload for a choice-based question within a submission."""
    model_config = ConfigDict(extra="forbid")

    question_key: str
    answer_family: Literal["choice"]
    answer_value: ChoiceAnswerValue


class FieldAnswerIn(BaseModel):
    """A single answer payload for an open-ended question within a submission."""
    model_config = ConfigDict(extra="forbid")

    question_key: str
    answer_family: Literal["field"]
    answer_value: FieldAnswerValue


class MatchingAnswerIn(BaseModel):
    """A single answer payload for a matching question within a submission."""
    model_config = ConfigDict(extra="forbid")

    question_key: str
    answer_family: Literal["matching"]
    answer_value: MatchingAnswerValue


class RatingAnswerIn(BaseModel):
    """A single answer payload for a rating question within a submission."""
    model_config = ConfigDict(extra="forbid")

    question_key: str
    answer_family: Literal["rating"]
    answer_value: RatingAnswerValue


AnswerIn = Annotated[
    ChoiceAnswerIn | FieldAnswerIn | MatchingAnswerIn | RatingAnswerIn,
    Field(discriminator="answer_family"),
]
