"""Stable field references, visibility, and survey-level workflow data."""

from typing import Annotated, Literal

from pydantic import Field, StrictBool

from app.schema.models.common.base import DataModel
from app.schema.types import (
    ConditionList,
    ConditionScalar,
    ConditionText,
    LimitedList,
    OrderedConditionValue,
    OutcomeId,
    ReadableId,
    SurveyFieldUuid,
)


class ValueComparison(DataModel):
    """Equality against a scalar answer value."""

    fieldUuid: SurveyFieldUuid
    operator: Literal["equals", "not_equals"]
    value: ConditionScalar


class OrderedComparison(DataModel):
    """Ordered comparison against a numeric or calendar-date answer value."""

    fieldUuid: SurveyFieldUuid
    operator: Literal["greater_than", "less_than"]
    value: OrderedConditionValue


class ContainsComparison(DataModel):
    """Text or choice-set membership comparison."""

    fieldUuid: SurveyFieldUuid
    operator: Literal["contains"]
    value: ConditionText


class AnsweredCondition(DataModel):
    """Test whether the field is answered; no comparison value is supplied."""

    fieldUuid: SurveyFieldUuid
    operator: Literal["is_answered"]


ComparisonCondition = Annotated[
    ValueComparison | OrderedComparison | ContainsComparison | AnsweredCondition,
    Field(discriminator="operator", title="ComparisonCondition"),
]


class AllCondition(DataModel):
    """Conjunction of one or more conditions."""

    all: ConditionList[Condition]


class AnyCondition(DataModel):
    """Disjunction of one or more conditions."""

    any: ConditionList[Condition]


class NotCondition(DataModel):
    """Negation of a condition."""

    condition: Condition = Field(alias="not")


Condition = ComparisonCondition | AllCondition | AnyCondition | NotCondition
AllCondition.model_rebuild()
AnyCondition.model_rebuild()
NotCondition.model_rebuild()


class AlwaysVisible(DataModel):
    """Unconditional visibility."""

    mode: Literal["always"]


class ConditionalVisibility(DataModel):
    """Visibility described by a condition."""

    mode: Literal["conditional"]
    condition: Condition


Visibility = Annotated[
    AlwaysVisible | ConditionalVisibility,
    Field(discriminator="mode", title="FieldVisibility"),
]


class FieldBehaviour(DataModel):
    """Optional field visibility data."""

    visibility: Visibility


class WorkflowRule(DataModel):
    """Condition and outcome data, without execution semantics."""

    id: ReadableId
    enabled: StrictBool
    when: Condition
    outcome: OutcomeId


class SurveyWorkflow(DataModel):
    """Survey-level rule collection."""

    rules: LimitedList[WorkflowRule]
