from __future__ import annotations

from typing import Annotated

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

# ── Condition requirements per question family ─────────────────────────────────


class ChoiceRequirementsIn(BaseModel):
    """Validation requirements for a choice-question condition."""

    model_config = ConfigDict(extra="forbid")

    required: list[SchemaIdStr] | None = Field(default=None, max_length=limits.RULE_ITEMS_MAX)
    forbidden: list[SchemaIdStr] | None = Field(default=None, max_length=limits.RULE_ITEMS_MAX)
    any_of: list[SchemaIdStr] | None = Field(default=None, max_length=limits.RULE_ITEMS_MAX)

    @model_validator(mode="after")
    def validate_has_at_least_one(self) -> ChoiceRequirementsIn:
        if self.required is None and self.forbidden is None and self.any_of is None:
            raise ValueError("choice requirements must specify at least one of: required, forbidden, any_of")
        return self


class MatchingRequirementsIn(BaseModel):
    """Validation requirements for a matching-question condition."""

    model_config = ConfigDict(extra="forbid")

    required: list[dict[SchemaIdStr, SchemaIdStr]] = Field(max_length=limits.RULE_ITEMS_MAX)

    @field_validator("required")
    @classmethod
    def validate_required(cls, value: list[dict[SchemaIdStr, SchemaIdStr]]) -> list[dict[SchemaIdStr, SchemaIdStr]]:
        if not value:
            raise ValueError("matching requirements must have at least one required pair")
        for pair in value:
            if len(pair) != 1:
                raise ValueError("each matching requirement must be a single-key dict mapping prompt_id to match_id")
        return value


class RatingRequirementsIn(BaseModel):
    """Validation requirements for a rating-question condition."""

    model_config = ConfigDict(extra="forbid")

    min: int | float | None = None
    max: int | float | None = None

    @model_validator(mode="after")
    def validate_has_at_least_one(self) -> RatingRequirementsIn:
        if self.min is None and self.max is None:
            raise ValueError("rating requirements must specify at least one of: min, max")
        return self


class NumberFieldRequirementsIn(BaseModel):
    """Validation requirements for a numeric field-question condition."""

    model_config = ConfigDict(extra="forbid")

    type: NumberFieldType
    operator: NumericFieldOperator
    value: int | float


class DateFieldRequirementsIn(BaseModel):
    """Validation requirements for a date field-question condition."""

    model_config = ConfigDict(extra="forbid")

    type: DateFieldType
    operator: DateFieldOperator
    value: DateValueStr

    @field_validator("value")
    @classmethod
    def validate_date_value(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("date value must be in YYYY-MM-DD format")
        return value


FieldRequirementsIn = NumberFieldRequirementsIn | DateFieldRequirementsIn


# ── Per-family condition blocks ────────────────────────────────────────────────


class ChoiceConditionIn(BaseModel):
    """Represents a condition block targeting a choice question."""

    model_config = ConfigDict(extra="forbid")

    target_id: SchemaIdStr
    family: ChoiceFamily
    requirements: ChoiceRequirementsIn


class MatchingConditionIn(BaseModel):
    """Represents a condition block targeting a matching question."""

    model_config = ConfigDict(extra="forbid")

    target_id: SchemaIdStr
    family: MatchingFamily
    requirements: MatchingRequirementsIn


class RatingConditionIn(BaseModel):
    """Represents a condition block targeting a rating question."""

    model_config = ConfigDict(extra="forbid")

    target_id: SchemaIdStr
    family: RatingFamily
    requirements: RatingRequirementsIn


class FieldConditionIn(BaseModel):
    """Represents a condition block targeting a field question."""

    model_config = ConfigDict(extra="forbid")

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

    model_config = ConfigDict(extra="forbid")

    match: IfMatch
    conditions: list[RuleConditionIn] = Field(max_length=limits.RULE_ITEMS_MAX)

    @field_validator("conditions")
    @classmethod
    def validate_conditions(cls, value: list[RuleConditionIn]) -> list[RuleConditionIn]:
        if not value:
            raise ValueError("conditions must contain at least one entry")
        return value


# ── Then / Else blocks ────────────────────────────────────────────────────────


class ThenSetItemIn(BaseModel):
    """Represents one visibility or required-state effect in a then block."""

    model_config = ConfigDict(extra="forbid")

    target_id: SchemaIdStr
    visible: bool | None = None
    required: bool | None = None

    @model_validator(mode="after")
    def validate_has_at_least_one_effect(self) -> ThenSetItemIn:
        if self.visible is None and self.required is None:
            raise ValueError("each then.set item must define at least one of: visible, required")
        return self


class ElseDoIn(BaseModel):
    """Represents the single navigation action performed by an else block."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    skip_to: SchemaIdStr | None = None
    end_and_submit: bool | None = None
    end_and_discard: bool | None = None

    @model_validator(mode="after")
    def validate_exactly_one_action(self) -> ElseDoIn:
        actions = [k for k in ("skip_to", "end_and_submit", "end_and_discard") if getattr(self, k) is not None]
        if len(actions) != 1:
            raise ValueError("else.do must specify exactly one action: skip_to, end_and_submit, or end_and_discard")
        return self


class RuleThenIn(BaseModel):
    """Represents the effects applied when a rule predicate matches."""

    model_config = ConfigDict(extra="forbid")

    set: list[ThenSetItemIn] = Field(max_length=limits.RULE_ITEMS_MAX)

    @field_validator("set")
    @classmethod
    def validate_set(cls, value: list[ThenSetItemIn]) -> list[ThenSetItemIn]:
        if not value:
            raise ValueError("then.set must contain at least one item")
        return value


class RuleElseIn(BaseModel):
    """Represents the fallback action when a rule predicate does not match."""

    model_config = ConfigDict(extra="forbid")

    do: ElseDoIn


# ── Top-level rule content schema ─────────────────────────────────────────────


class RuleSchemaIn(BaseModel):
    """Represents the full rule content stored in question_schema for a rule node."""

    model_config = ConfigDict(extra="forbid")

    id: SchemaIdStr
    if_: RuleIfIn = Field(validation_alias="if", serialization_alias="if")
    then: RuleThenIn
    else_: RuleElseIn | None = Field(default=None, validation_alias="else", serialization_alias="else")
