"""Check that canonical answer values preserve types and reject legacy shapes."""

import pytest
from pydantic import ValidationError

from app.schema.models.survey_document.answers import AnsweredAnswer


@pytest.mark.parametrize("value", [1, 1.5])
def test_number_preserves_integer_and_decimal_values(value: int | float) -> None:
    answer = AnsweredAnswer.model_validate(
        {
            "state": "answered",
            "answer_spec": {"type": "number", "required": True},
            "answer_value": value,
        }
    )
    assert type(answer.answer_value) is type(value)
    assert answer.answer_value == value


@pytest.mark.parametrize(
    ("spec", "value"),
    [
        ({"type": "choice_set", "required": True}, {"selected": ["o1", "o2"]}),
        ({"type": "date", "required": True}, "18-06-2026"),
        (
            {"type": "object", "required": True, "valueType": "matching"},
            {"pairs": [{"prompt_id": "p1", "match_id": "m1"}]},
        ),
    ],
)
def test_answer_rejects_legacy_value_shape(spec: dict[str, str | bool], value: object) -> None:
    with pytest.raises(ValidationError):
        AnsweredAnswer.model_validate({"state": "answered", "answer_spec": spec, "answer_value": value})
