from __future__ import annotations

import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schema.api import limits
from app.schema.api.common.fields import SchemaIdStr
from app.schema.enums import AnswerFamily, SubmissionAnswerState

_STRICT = ConfigDict(extra="forbid", strict=True)

DateAnswerStr = Annotated[str, Field(max_length=limits.DATE_VALUE_MAX)]


class ChoiceAnswerValueIn(BaseModel):
    """Answer value for a choice question."""

    model_config = _STRICT

    selected: list[SchemaIdStr] = Field(min_length=1, max_length=limits.QUESTION_ITEMS_MAX)

    @field_validator("selected")
    @classmethod
    def validate_unique_selected(cls, value: list[SchemaIdStr]) -> list[SchemaIdStr]:
        if len(value) != len(set(value)):
            raise ValueError("selected option ids must be unique")
        return value


class ShortTextFieldAnswerValueIn(BaseModel):
    """Answer value for a short-text field question."""

    model_config = _STRICT

    field_type: Literal["short_text"]
    text: str = Field(min_length=1, max_length=limits.ANSWER_TEXT_MAX)


class LongTextFieldAnswerValueIn(BaseModel):
    """Answer value for a long-text field question."""

    model_config = _STRICT

    field_type: Literal["long_text"]
    text: str = Field(min_length=1, max_length=limits.ANSWER_TEXT_MAX)


class EmailFieldAnswerValueIn(BaseModel):
    """Answer value for an email field question."""

    model_config = _STRICT

    field_type: Literal["email"]
    email: EmailStr


class NumberFieldAnswerValueIn(BaseModel):
    """Answer value for a numeric field question."""

    model_config = _STRICT

    field_type: Literal["number"]
    number: int | float


class DateFieldAnswerValueIn(BaseModel):
    """Answer value for a date field question."""

    model_config = _STRICT

    field_type: Literal["date"]
    date: DateAnswerStr

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("date must be in YYYY-MM-DD format")
        return value


class PhoneFieldAnswerValueIn(BaseModel):
    """Answer value for a phone field question."""

    model_config = _STRICT

    field_type: Literal["phone"]
    phone: str = Field(min_length=1, max_length=64)


FieldAnswerValueIn = Annotated[
    ShortTextFieldAnswerValueIn
    | LongTextFieldAnswerValueIn
    | EmailFieldAnswerValueIn
    | NumberFieldAnswerValueIn
    | DateFieldAnswerValueIn
    | PhoneFieldAnswerValueIn,
    Field(discriminator="field_type"),
]


class MatchingAnswerPairIn(BaseModel):
    """One prompt-to-match pair in a matching answer."""

    model_config = _STRICT

    prompt_id: SchemaIdStr
    match_id: SchemaIdStr


class MatchingAnswerValueIn(BaseModel):
    """Answer value for a matching question."""

    model_config = _STRICT

    pairs: list[MatchingAnswerPairIn] = Field(
        min_length=1,
        max_length=limits.QUESTION_ITEMS_MAX,
    )

    @field_validator("pairs")
    @classmethod
    def validate_unique_prompt_ids(
        cls,
        value: list[MatchingAnswerPairIn],
    ) -> list[MatchingAnswerPairIn]:
        prompt_ids = [pair.prompt_id for pair in value]
        if len(prompt_ids) != len(set(prompt_ids)):
            raise ValueError("matching answer cannot contain duplicate prompt_id values")
        return value


class SliderRatingAnswerValueIn(BaseModel):
    """Answer value for a slider rating question."""

    model_config = _STRICT

    variant: Literal["slider"]
    number: int | float


class StarsRatingAnswerValueIn(BaseModel):
    """Answer value for a star rating question."""

    model_config = _STRICT

    variant: Literal["stars"]
    number: int


class EmojiRatingAnswerValueIn(BaseModel):
    """Answer value for an emoji rating question."""

    model_config = _STRICT

    variant: Literal["emoji"]
    number: int


RatingAnswerValueIn = Annotated[
    SliderRatingAnswerValueIn | StarsRatingAnswerValueIn | EmojiRatingAnswerValueIn,
    Field(discriminator="variant"),
]

SubmissionAnswerValueIn = ChoiceAnswerValueIn | FieldAnswerValueIn | MatchingAnswerValueIn | RatingAnswerValueIn


class SaveSubmissionSessionAnswerRequest(BaseModel):
    """Request body for saving or clearing one respondent answer revision."""

    model_config = ConfigDict(extra="forbid")

    client_mutation_id: UUID
    state: SubmissionAnswerState
    answer_family: AnswerFamily | None = None
    answer_value: SubmissionAnswerValueIn | None = None

    @model_validator(mode="after")
    def validate_answer_state(self) -> SaveSubmissionSessionAnswerRequest:
        if self.state == "answered":
            if self.answer_family is None:
                raise ValueError("answer_family is required when state is 'answered'.")
            if self.answer_value is None:
                raise ValueError("answer_value is required when state is 'answered'.")
            self._validate_answer_value_matches_family()
            return self

        if self.answer_family is not None:
            raise ValueError("answer_family must be omitted when state is 'cleared'.")
        if self.answer_value is not None:
            raise ValueError("answer_value must be omitted when state is 'cleared'.")
        return self

    def _validate_answer_value_matches_family(self) -> None:
        if self.answer_family == "choice" and not isinstance(self.answer_value, ChoiceAnswerValueIn):
            raise ValueError("answer_value must be a choice answer when answer_family is 'choice'.")
        if self.answer_family == "field" and not isinstance(
            self.answer_value,
            (
                ShortTextFieldAnswerValueIn,
                LongTextFieldAnswerValueIn,
                EmailFieldAnswerValueIn,
                NumberFieldAnswerValueIn,
                DateFieldAnswerValueIn,
                PhoneFieldAnswerValueIn,
            ),
        ):
            raise ValueError("answer_value must be a field answer when answer_family is 'field'.")
        if self.answer_family == "matching" and not isinstance(self.answer_value, MatchingAnswerValueIn):
            raise ValueError("answer_value must be a matching answer when answer_family is 'matching'.")
        if self.answer_family == "rating" and not isinstance(
            self.answer_value,
            (
                SliderRatingAnswerValueIn,
                StarsRatingAnswerValueIn,
                EmojiRatingAnswerValueIn,
            ),
        ):
            raise ValueError("answer_value must be a rating answer when answer_family is 'rating'.")
