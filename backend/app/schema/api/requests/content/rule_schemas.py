from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RuleOperator = Literal[
    "equals",
    "not_equals",
    "is_answered",
    "is_empty",
    "contains",
    "contains_any",
    "contains_all",
    "gt",
    "gte",
    "lt",
    "lte",
    "between",
]


ScalarRuleValue = str | int | float | bool | None


class SimpleConditionIn(BaseModel):
    """Represents a simple condition that compares a single fact to a value using an operator."""
    model_config = ConfigDict(extra="forbid")

    fact: str
    operator: RuleOperator
    value: ScalarRuleValue | list[ScalarRuleValue] | None = None

    @field_validator("fact")
    @classmethod
    def validate_fact(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("fact must not be blank")
        if not value.startswith("answers."):
            raise ValueError("fact must start with 'answers.'")
        question_key = value.removeprefix("answers.")
        if not question_key.strip():
            raise ValueError("fact must reference a question key after 'answers.'")
        return value

    @model_validator(mode="after")
    def validate_operator_value_shape(self) -> SimpleConditionIn:
        no_value_ops = {"is_answered", "is_empty"}
        list_ops = {"contains_any", "contains_all"}
        between_ops = {"between"}
        single_value_ops = {
            "equals",
            "not_equals",
            "contains",
            "gt",
            "gte",
            "lt",
            "lte",
        }

        if self.operator in no_value_ops:
            if self.value is not None:
                raise ValueError(f"operator '{self.operator}' must not include value")
            return self

        if self.operator in list_ops:
            if not isinstance(self.value, list) or len(self.value) == 0:
                raise ValueError(f"operator '{self.operator}' requires a non-empty list value")
            return self

        if self.operator in between_ops:
            if not isinstance(self.value, list) or len(self.value) != 2:
                raise ValueError("operator 'between' requires a list of exactly two values")
            if not all(isinstance(item, (int, float)) for item in self.value):
                raise ValueError("operator 'between' requires two numeric values")
            return self

        if self.operator in single_value_ops:
            if isinstance(self.value, list) or self.value is None:
                raise ValueError(f"operator '{self.operator}' requires a single scalar value")
            return self

        return self


class AllConditionIn(BaseModel):
    """Represents a compound condition where all sub-conditions must be true."""
    model_config = ConfigDict(extra="forbid")

    all: list[ConditionIn]

    @field_validator("all")
    @classmethod
    def validate_all(cls, value: list[ConditionIn]) -> list[ConditionIn]:
        if not value:
            raise ValueError("all must contain at least one condition")
        return value


class AnyConditionIn(BaseModel):
    """Represents a compound condition where at least one sub-condition must be true."""
    model_config = ConfigDict(extra="forbid")

    any: list[ConditionIn]

    @field_validator("any")
    @classmethod
    def validate_any(cls, value: list[ConditionIn]) -> list[ConditionIn]:
        if not value:
            raise ValueError("any must contain at least one condition")
        return value


class NotConditionIn(BaseModel):
    """Represents a compound condition where the sub-condition must not be true."""
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    not_: ConditionIn = Field(
        validation_alias="not",
        serialization_alias="not",
    )


ConditionIn = Annotated[
    SimpleConditionIn | AllConditionIn | AnyConditionIn | NotConditionIn,
    Field(discriminator=None),
]


class RuleEffectsIn(BaseModel):
    """Represents the effects that a rule can have on a question, such as making it visible, required, or disabled."""
    model_config = ConfigDict(extra="forbid")

    visible: bool | None = None
    required: bool | None = None
    disabled: bool | None = None

    @model_validator(mode="after")
    def validate_has_at_least_one_effect(self) -> RuleEffectsIn:
        if self.visible is None and self.required is None and self.disabled is None:
            raise ValueError("effects must define at least one effect")
        return self


class RuleSchemaIn(BaseModel):
    """Represents the schema of a rule, including its target, sort order, condition, and effects."""
    model_config = ConfigDict(extra="forbid")

    target: str
    sort_order: int = 0
    condition: ConditionIn
    effects: RuleEffectsIn

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("target must not be blank")
        return value
