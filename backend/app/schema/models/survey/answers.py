"""Reusable answered and cleared data, without HTTP operation metadata."""

from typing import Annotated, Literal, Self

from pydantic import ConfigDict, Field, model_validator

from app.schema import limits
from app.schema.models.common.base import DataModel
from app.schema.models.survey.answer_spec import AnswerSpec
from app.schema.models.survey.answer_value import AnswerValue
from app.schema.models.survey.validators import validate_answer_value


class AnsweredAnswer(DataModel):
    """An answered value with its specification."""

    # Preserve the long-form answer ceiling across typed value alternatives.
    model_config = ConfigDict(str_max_length=limits.LONG_STRING_MAX)

    state: Literal["answered"]
    answer_spec: AnswerSpec
    answer_value: AnswerValue

    @model_validator(mode="after")
    def validate_value(self) -> Self:
        validate_answer_value(self.answer_spec, self.answer_value)
        return self


class ClearedAnswer(DataModel):
    """Explicitly cleared answer data with no value."""

    state: Literal["cleared"]
    answer_spec: AnswerSpec | None = None


AnswerData = Annotated[AnsweredAnswer | ClearedAnswer, Field(discriminator="state", title="AnswerData")]
