"""Canonical per-family answer-value models.

This module is the single source of truth for the shape of a submitted answer
value, per question family. The same models are reused by:

- request validation (``SaveSubmissionSessionAnswerRequest``),
- the typed respondent response (``SubmissionSessionAnswerResponse``),
- admin decrypt result typing (``DecryptedAnswerResult``).

The encrypted plaintext payload (``app.crypto.payload``) intentionally stores
``answer_value`` as the JSON form of one of these models, *without* recording
which family it belongs to. The family is reconstructed from the survey
definition at decrypt time, so callers that have the family on hand use
``parse_answer_value`` to validate a raw value back into a concrete model.

The four families share no common discriminator key (choice -> ``selected``,
field -> ``field_type``, matching -> ``pairs``, rating -> ``variant``), so the
top-level ``SubmissionAnswerValue`` is a plain union, not a discriminated one.
Use ``parse_answer_value`` wherever the family is known.

This module imports only from ``schema/api`` and ``schema/enums`` — never ORM.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter, field_validator

from app.schema.api import limits
from app.schema.api.common.fields import (
    AnswerNumber,
    EmojiRatingNumber,
    PhoneNumber,
    SchemaIdStr,
    SliderRatingNumber,
    StarsRatingNumber,
)
from app.schema.enums import AnswerFamily

_STRICT = ConfigDict(extra="forbid", strict=True)

DateAnswerStr = Annotated[str, Field(max_length=limits.DATE_VALUE_MAX)]


class ChoiceAnswerValue(BaseModel):
    """Answer value for a choice question."""

    model_config = _STRICT

    selected: list[SchemaIdStr] = Field(min_length=1, max_length=limits.QUESTION_ITEMS_MAX)

    @field_validator("selected")
    @classmethod
    def validate_unique_selected(cls, value: list[SchemaIdStr]) -> list[SchemaIdStr]:
        if len(value) != len(set(value)):
            raise ValueError("selected option ids must be unique")
        return value


class ShortTextFieldAnswerValue(BaseModel):
    """Answer value for a short-text field question."""

    model_config = _STRICT

    field_type: Literal["short_text"]
    text: str = Field(min_length=1, max_length=limits.ANSWER_TEXT_MAX)


class LongTextFieldAnswerValue(BaseModel):
    """Answer value for a long-text field question."""

    model_config = _STRICT

    field_type: Literal["long_text"]
    text: str = Field(min_length=1, max_length=limits.ANSWER_TEXT_MAX)


class EmailFieldAnswerValue(BaseModel):
    """Answer value for an email field question."""

    model_config = _STRICT

    field_type: Literal["email"]
    email: EmailStr


class NumberFieldAnswerValue(BaseModel):
    """Answer value for a numeric field question."""

    model_config = _STRICT

    field_type: Literal["number"]
    number: AnswerNumber


class DateFieldAnswerValue(BaseModel):
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


class PhoneFieldAnswerValue(BaseModel):
    """Answer value for a phone field question."""

    model_config = _STRICT

    field_type: Literal["phone"]
    phone: PhoneNumber


FieldAnswerValue = Annotated[
    ShortTextFieldAnswerValue
    | LongTextFieldAnswerValue
    | EmailFieldAnswerValue
    | NumberFieldAnswerValue
    | DateFieldAnswerValue
    | PhoneFieldAnswerValue,
    Field(discriminator="field_type"),
]


class MatchingAnswerPair(BaseModel):
    """One prompt-to-match pair in a matching answer."""

    model_config = _STRICT

    prompt_id: SchemaIdStr
    match_id: SchemaIdStr


class MatchingAnswerValue(BaseModel):
    """Answer value for a matching question."""

    model_config = _STRICT

    pairs: list[MatchingAnswerPair] = Field(
        min_length=1,
        max_length=limits.QUESTION_ITEMS_MAX,
    )

    @field_validator("pairs")
    @classmethod
    def validate_unique_prompt_ids(
        cls,
        value: list[MatchingAnswerPair],
    ) -> list[MatchingAnswerPair]:
        prompt_ids = [pair.prompt_id for pair in value]
        if len(prompt_ids) != len(set(prompt_ids)):
            raise ValueError("matching answer cannot contain duplicate prompt_id values")
        return value


class SliderRatingAnswerValue(BaseModel):
    """Answer value for a slider rating question."""

    model_config = _STRICT

    variant: Literal["slider"]
    number: SliderRatingNumber


class StarsRatingAnswerValue(BaseModel):
    """Answer value for a star rating question."""

    model_config = _STRICT

    variant: Literal["stars"]
    number: StarsRatingNumber


class EmojiRatingAnswerValue(BaseModel):
    """Answer value for an emoji rating question."""

    model_config = _STRICT

    variant: Literal["emoji"]
    number: EmojiRatingNumber


RatingAnswerValue = Annotated[
    SliderRatingAnswerValue | StarsRatingAnswerValue | EmojiRatingAnswerValue,
    Field(discriminator="variant"),
]

SubmissionAnswerValue = ChoiceAnswerValue | FieldAnswerValue | MatchingAnswerValue | RatingAnswerValue


# Per-family adapters for validating a raw value when the family is known
# (e.g. at decrypt time, where the family is reconstructed from the survey
# definition rather than read from the payload).
ANSWER_VALUE_MODEL_BY_FAMILY: dict[AnswerFamily, TypeAdapter] = {
    "choice": TypeAdapter(ChoiceAnswerValue),
    "field": TypeAdapter(FieldAnswerValue),
    "matching": TypeAdapter(MatchingAnswerValue),
    "rating": TypeAdapter(RatingAnswerValue),
}


def parse_answer_value(family: AnswerFamily, raw: object) -> SubmissionAnswerValue:
    """Validate a raw answer value into the concrete model for ``family``.

    Raises ``pydantic.ValidationError`` if ``raw`` does not match the family's
    canonical shape, and ``KeyError`` if ``family`` is not a known family.
    """
    adapter = ANSWER_VALUE_MODEL_BY_FAMILY[family]
    return adapter.validate_python(raw)
