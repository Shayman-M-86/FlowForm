from __future__ import annotations

import re
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schema.api import limits
from app.schema.api.enums import (
    ChoiceFamily,
    DateFieldOperator,
    DateFieldType,
    FieldFamily,
    IfMatch,
    MatchingFamily,
    NumberFieldType,
    NumericFieldOperator,
    RatingFamily,
)
from app.schema.api.requests.field_types import SchemaIdStr

DateValueStr = Annotated[str, Field(max_length=limits.DATE_VALUE_MAX)]

_STRICT = ConfigDict(extra="forbid", populate_by_name=True)


# ── Condition requirements per question family ─────────────────────────────────


class ChoiceRequirementsIn(BaseModel):
    """Validation requirements for a choice-question condition."""

    model_config = _STRICT

    required: list[SchemaIdStr] = Field(default_factory=list, max_length=limits.RULE_ITEMS_MAX)
    forbidden: list[SchemaIdStr] = Field(default_factory=list, max_length=limits.RULE_ITEMS_MAX)
    any_of: list[SchemaIdStr] = Field(default_factory=list, max_length=limits.RULE_ITEMS_MAX)

    @model_validator(mode="after")
    def validate_requirements(self) -> Self:
        if not self.required and not self.forbidden and not self.any_of:
            raise ValueError("choice requirements must contain at least one of: required, forbidden, any_of")

        conflicting = (
            set(self.required) & set(self.forbidden)
            | set(self.any_of) & set(self.forbidden)
        )
        if conflicting:
            raise ValueError(
                f"choice options cannot be both allowed and forbidden: {sorted(conflicting)}"
            )

        return self


class MatchingPairIn(BaseModel):
    """A single prompt-to-match pairing in a matching condition."""

    model_config = _STRICT

    prompt_id: SchemaIdStr
    match_id: SchemaIdStr


class MatchingRequirementsIn(BaseModel):
    """Validation requirements for a matching-question condition."""

    model_config = _STRICT

    required: list[MatchingPairIn] = Field(min_length=1, max_length=limits.RULE_ITEMS_MAX)


class RatingRequirementsIn(BaseModel):
    """Validation requirements for a rating-question condition."""

    model_config = _STRICT

    min: int | float | None = None
    max: int | float | None = None

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.min is None and self.max is None:
            raise ValueError("rating requirements must specify at least one of: min, max")

        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("rating min cannot be greater than max")

        return self


class NumberFieldRequirementsIn(BaseModel):
    """Validation requirements for a numeric field-question condition."""

    model_config = _STRICT

    type: NumberFieldType
    operator: NumericFieldOperator
    value: int | float


class DateFieldRequirementsIn(BaseModel):
    """Validation requirements for a date field-question condition."""

    model_config = _STRICT

    type: DateFieldType
    operator: DateFieldOperator
    value: DateValueStr

    @field_validator("value")
    @classmethod
    def validate_date_value(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("date value must be in YYYY-MM-DD format")
        return value


FieldRequirementsIn = Annotated[
    NumberFieldRequirementsIn | DateFieldRequirementsIn,
    Field(discriminator="type"),
]


# ── Per-family condition blocks ────────────────────────────────────────────────


class ChoiceConditionIn(BaseModel):
    """Represents a condition block targeting a choice question."""

    model_config = _STRICT

    target_id: SchemaIdStr
    family: ChoiceFamily
    requirements: ChoiceRequirementsIn


class MatchingConditionIn(BaseModel):
    """Represents a condition block targeting a matching question."""

    model_config = _STRICT

    target_id: SchemaIdStr
    family: MatchingFamily
    requirements: MatchingRequirementsIn


class RatingConditionIn(BaseModel):
    """Represents a condition block targeting a rating question."""

    model_config = _STRICT

    target_id: SchemaIdStr
    family: RatingFamily
    requirements: RatingRequirementsIn


class FieldConditionIn(BaseModel):
    """Represents a condition block targeting a field question."""

    model_config = _STRICT

    target_id: SchemaIdStr
    family: FieldFamily
    requirements: FieldRequirementsIn


RuleConditionIn = Annotated[
    ChoiceConditionIn | MatchingConditionIn | RatingConditionIn | FieldConditionIn,
    Field(discriminator="family"),
]


# ── If block ──────────────────────────────────────────────────────────────────


class RuleIfIn(BaseModel):
    """Represents the rule predicate and how its conditions are matched."""

    model_config = _STRICT

    match: IfMatch
    conditions: list[RuleConditionIn] = Field(min_length=1, max_length=limits.RULE_ITEMS_MAX)


# ── State changes applied by a branch ─────────────────────────────────────────


class RuleSetItemIn(BaseModel):
    """Represents one visibility or required-state change applied by a branch."""

    model_config = _STRICT

    target_id: SchemaIdStr
    visible: bool | None = None
    required: bool | None = None

    @model_validator(mode="after")
    def validate_change(self) -> Self:
        if self.visible is None and self.required is None:
            raise ValueError("set item must update at least one of: visible, required")
        return self


# ── Navigation actions ────────────────────────────────────────────────────────


class SkipToActionIn(BaseModel):
    """Navigation action that jumps to a specific question."""

    model_config = _STRICT

    skip_to: SchemaIdStr


class EndAndSubmitActionIn(BaseModel):
    """Navigation action that ends the survey and submits the response."""

    model_config = _STRICT

    end_and_submit: bool = True


class EndAndDiscardActionIn(BaseModel):
    """Navigation action that ends the survey and discards the response."""

    model_config = _STRICT

    end_and_discard: bool = True


RuleDoIn = Annotated[
    SkipToActionIn | EndAndSubmitActionIn | EndAndDiscardActionIn,
    Field(discriminator=None),
]


# ── Shared then / else branch ─────────────────────────────────────────────────


class RuleBranchIn(BaseModel):
    """Represents the effects applied by a then or else branch."""

    model_config = _STRICT

    set: list[RuleSetItemIn] | None = Field(default=None, min_length=1, max_length=limits.RULE_ITEMS_MAX)
    do: RuleDoIn | None = None

    @model_validator(mode="after")
    def validate_branch(self) -> Self:
        if self.set is None and self.do is None:
            raise ValueError("rule branch must contain at least one of: set, do")
        return self


# ── Top-level rule content schema ─────────────────────────────────────────────


class RuleSchemaIn(BaseModel):
    """Represents the full rule content stored in question_schema for a rule node."""

    model_config = _STRICT

    if_: RuleIfIn = Field(validation_alias="if", serialization_alias="if")
    then: RuleBranchIn
    else_: RuleBranchIn | None = Field(default=None, validation_alias="else", serialization_alias="else")
