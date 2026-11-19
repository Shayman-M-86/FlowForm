"""Value checks against a submitted answer specification, without provenance claims."""

import math
from datetime import date
from uuid import UUID

from pydantic import TypeAdapter

from app.schema.models.survey_document.answer_spec import (
    AnswerSpec,
    ChoiceSetAnswerSpec,
    DateAnswerSpec,
    MatchingAnswerSpec,
    NumericAnswerSpec,
    StringAnswerSpec,
)
from app.schema.models.survey_document.answer_value import AnswerValue, MatchingValue
from app.schema.types import ChoiceOptionUuid

_UUID = TypeAdapter(ChoiceOptionUuid)


def _validate_uuid(value: object) -> None:
    if isinstance(value, UUID):
        return
    if not isinstance(value, str):
        raise ValueError("option identifiers must be UUID strings")
    _UUID.validate_python(value, strict=False)


def validate_answer_value(spec: AnswerSpec, value: AnswerValue) -> None:
    """Check a value against its submitted spec, without asserting provenance."""
    if isinstance(spec, StringAnswerSpec):
        if not isinstance(value, str):
            raise ValueError("string answers require a string")
        if spec.constraints is not None:
            bounds = spec.constraints
            if bounds.minLength is not None and len(value) < bounds.minLength:
                raise ValueError("answer is shorter than minLength")
            if bounds.maxLength is not None and len(value) > bounds.maxLength:
                raise ValueError("answer is longer than maxLength")
    elif isinstance(spec, NumericAnswerSpec):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("answer must match the specified numeric type")
        if (isinstance(value, float) and not math.isfinite(value)) or (
            spec.type == "integer" and type(value) is not int
        ):
            raise ValueError("answer must match the specified numeric type")
        if spec.constraints is not None:
            bounds = spec.constraints
            if bounds.min is not None and value < bounds.min:
                raise ValueError("answer is below min")
            if bounds.max is not None and value > bounds.max:
                raise ValueError("answer exceeds max")
    elif isinstance(spec, DateAnswerSpec):
        if type(value) is date:
            parsed = value
        elif isinstance(value, str):
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError("dates must use YYYY-MM-DD")
        else:
            raise ValueError("date answers require a date string")
        if spec.constraints is not None:
            if spec.constraints.min is not None and parsed < spec.constraints.min:
                raise ValueError("answer is before min")
            if spec.constraints.max is not None and parsed > spec.constraints.max:
                raise ValueError("answer is after max")
    elif isinstance(spec, ChoiceSetAnswerSpec):
        if not isinstance(value, list):
            raise ValueError("choice_set answers require an array of option UUIDs")
        for option in value:
            _validate_uuid(option)
        if spec.constraints is not None:
            bounds = spec.constraints
            if bounds.minSelections is not None and len(value) < bounds.minSelections:
                raise ValueError("answer has fewer than minSelections")
            if bounds.maxSelections is not None and len(value) > bounds.maxSelections:
                raise ValueError("answer has more than maxSelections")
    elif isinstance(spec, MatchingAnswerSpec):
        if not isinstance(value, MatchingValue):
            raise ValueError("matching answers require typed prompt-to-match pairs")
    elif spec.type == "choice":
        _validate_uuid(value)
    elif spec.type == "boolean" and type(value) is not bool:
        raise ValueError("boolean answers require true or false")
