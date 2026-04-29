from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ── Condition requirements per question family ─────────────────────────────────

class ChoiceRequirementsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: list[str] | None = None
    forbidden: list[str] | None = None
    any_of: list[str] | None = None

    @model_validator(mode="after")
    def validate_has_at_least_one(self) -> ChoiceRequirementsIn:
        if self.required is None and self.forbidden is None and self.any_of is None:
            raise ValueError("choice requirements must specify at least one of: required, forbidden, any_of")
        return self


class MatchingRequirementsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: list[dict[str, str]]

    @field_validator("required")
    @classmethod
    def validate_required(cls, value: list[dict[str, str]]) -> list[dict[str, str]]:
        if not value:
            raise ValueError("matching requirements must have at least one required pair")
        for pair in value:
            if len(pair) != 1:
                raise ValueError("each matching requirement must be a single-key dict mapping prompt_id to match_id")
        return value


class RatingRequirementsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: int | float | None = None
    max: int | float | None = None

    @model_validator(mode="after")
    def validate_has_at_least_one(self) -> RatingRequirementsIn:
        if self.min is None and self.max is None:
            raise ValueError("rating requirements must specify at least one of: min, max")
        return self


FieldOperator = Literal["LT", "LTE", "GT", "GTE", "EQ", "NEQ", "before", "after"]


class NumberFieldRequirementsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["number"]
    operator: Literal["LT", "LTE", "GT", "GTE", "EQ", "NEQ"]
    value: int | float


class DateFieldRequirementsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["date"]
    operator: Literal["before", "after"]
    value: str

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
    model_config = ConfigDict(extra="forbid")

    target_id: str
    family: Literal["choice"]
    requirements: ChoiceRequirementsIn

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("target_id must not be blank")
        return value


class MatchingConditionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    family: Literal["matching"]
    requirements: MatchingRequirementsIn

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("target_id must not be blank")
        return value


class RatingConditionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    family: Literal["rating"]
    requirements: RatingRequirementsIn

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("target_id must not be blank")
        return value


class FieldConditionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    family: Literal["field"]
    requirements: FieldRequirementsIn

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("target_id must not be blank")
        return value


RuleConditionIn = Annotated[
    ChoiceConditionIn | MatchingConditionIn | RatingConditionIn | FieldConditionIn,
    Field(discriminator="family"),
]


# ── If block ──────────────────────────────────────────────────────────────────

IfMatch = Literal["ALL", "ANY", "NONE"]


class RuleIfIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match: IfMatch
    conditions: list[RuleConditionIn]

    @field_validator("conditions")
    @classmethod
    def validate_conditions(cls, value: list[RuleConditionIn]) -> list[RuleConditionIn]:
        if not value:
            raise ValueError("conditions must contain at least one entry")
        return value


# ── Then / Else blocks ────────────────────────────────────────────────────────

class ThenSetItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    visible: bool | None = None
    required: bool | None = None

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("target_id must not be blank")
        return value

    @model_validator(mode="after")
    def validate_has_at_least_one_effect(self) -> ThenSetItemIn:
        if self.visible is None and self.required is None:
            raise ValueError("each then.set item must define at least one of: visible, required")
        return self


SkipAction = Literal["skip_to", "end_and_submit", "end_and_discard"]


class ElseDoIn(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    skip_to: str | None = None
    end_and_submit: bool | None = None
    end_and_discard: bool | None = None

    @model_validator(mode="after")
    def validate_exactly_one_action(self) -> ElseDoIn:
        actions = [k for k in ("skip_to", "end_and_submit", "end_and_discard") if getattr(self, k) is not None]
        if len(actions) != 1:
            raise ValueError("else.do must specify exactly one action: skip_to, end_and_submit, or end_and_discard")
        return self


class RuleThenIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    set: list[ThenSetItemIn]

    @field_validator("set")
    @classmethod
    def validate_set(cls, value: list[ThenSetItemIn]) -> list[ThenSetItemIn]:
        if not value:
            raise ValueError("then.set must contain at least one item")
        return value


class RuleElseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    do: ElseDoIn


# ── Top-level rule content schema ─────────────────────────────────────────────

class RuleSchemaIn(BaseModel):
    """Represents the full rule content stored in question_schema for a rule node."""

    model_config = ConfigDict(extra="forbid")

    id: str
    if_: RuleIfIn = Field(validation_alias="if", serialization_alias="if")
    then: RuleThenIn
    else_: RuleElseIn | None = Field(default=None, validation_alias="else", serialization_alias="else")

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id must not be blank")
        return value
