"""Accepted answer shapes shared by survey fields and answer submissions."""

from typing import Annotated, Literal, Self

from pydantic import Field, StrictBool, model_validator

from app.schema.models.common.base import DataModel
from app.schema.types import AnswerInteger, AnswerLength, AnswerNumber, CalendarDate


class NumericAnswerBounds(DataModel):
    """Inclusive numeric bounds."""

    min: AnswerInteger | AnswerNumber | None = None
    max: AnswerInteger | AnswerNumber | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must not exceed max")
        return self


class TextAnswerBounds(DataModel):
    """String length bounds."""

    minLength: AnswerLength | None = None
    maxLength: AnswerLength | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        if self.minLength is not None and self.maxLength is not None and self.minLength > self.maxLength:
            raise ValueError("minLength must not exceed maxLength")
        return self


class SelectionAnswerBounds(DataModel):
    """Bounds on the number of selected options."""

    minSelections: AnswerLength | None = None
    maxSelections: AnswerLength | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        if (
            self.minSelections is not None
            and self.maxSelections is not None
            and self.minSelections > self.maxSelections
        ):
            raise ValueError("minSelections must not exceed maxSelections")
        return self


class StringAnswerSpec(DataModel):
    """Text value specification."""

    type: Literal["string"]
    required: StrictBool
    constraints: TextAnswerBounds | None = None


class NumericAnswerSpec(DataModel):
    """Integer or decimal-capable number specification."""

    type: Literal["integer", "number"]
    required: StrictBool
    constraints: NumericAnswerBounds | None = None


class BooleanAnswerSpec(DataModel):
    """Boolean value specification."""

    type: Literal["boolean"]
    required: StrictBool


class DateAnswerBounds(DataModel):
    """Inclusive calendar-date bounds."""

    min: CalendarDate | None = None
    max: CalendarDate | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must not exceed max")
        return self


class DateAnswerSpec(DataModel):
    """Calendar date specification."""

    type: Literal["date"]
    required: StrictBool
    constraints: DateAnswerBounds | None = None


class ChoiceAnswerSpec(DataModel):
    """Single option UUID specification."""

    type: Literal["choice"]
    required: StrictBool


class ChoiceSetAnswerSpec(DataModel):
    """Array of option UUIDs specification."""

    type: Literal["choice_set"]
    required: StrictBool
    constraints: SelectionAnswerBounds | None = None


class MatchingAnswerSpec(DataModel):
    """The documented structured matching value specification."""

    type: Literal["object"]
    required: StrictBool
    valueType: Literal["matching"]


AnswerSpec = Annotated[
    StringAnswerSpec
    | NumericAnswerSpec
    | BooleanAnswerSpec
    | DateAnswerSpec
    | ChoiceAnswerSpec
    | ChoiceSetAnswerSpec
    | MatchingAnswerSpec,
    Field(discriminator="type", title="AnswerSpec"),
]
