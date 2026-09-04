"""Unit tests for validating answers against resolved document fields."""

from __future__ import annotations

import datetime

import pytest

from app.domain.errors import InvalidFieldAnswerError
from app.domain.survey_document_answer_validation import validate_field_answer
from app.schema.api.content.survey_document import SurveyField


def _field(*, interaction: dict[str, object], response: dict[str, object]) -> SurveyField:
    return SurveyField.model_validate(
        {
            "id": "field_answer",
            "key": "answer",
            "prompt": "Answer",
            "interaction": interaction,
            "response": response,
        }
    )


def test_text_answer_enforces_length_bounds() -> None:
    field = _field(
        interaction={"kind": "text"},
        response={"type": "string", "validation": {"min_length": 2, "max_length": 4}},
    )

    assert validate_field_answer(field, "yes") == "yes"
    with pytest.raises(InvalidFieldAnswerError, match="shorter"):
        validate_field_answer(field, "x")


@pytest.mark.parametrize(
    ("answer_format", "valid", "invalid"),
    [
        ("email", "person@example.com", "not-an-email"),
        ("url", "https://example.com/form", "not a url"),
        ("tel", "+61 2 1234 5678", "call me"),
    ],
)
def test_string_format_comes_from_response_validation(
    answer_format: str,
    valid: str,
    invalid: str,
) -> None:
    field = _field(
        interaction={"kind": "text", "presentation": "plain"},
        response={"type": "string", "validation": {"format": answer_format}},
    )

    assert validate_field_answer(field, valid) == valid
    with pytest.raises(InvalidFieldAnswerError):
        validate_field_answer(field, invalid)


def test_number_answer_is_parsed_strictly_and_enforces_bounds() -> None:
    field = _field(
        interaction={"kind": "number"},
        response={"type": "integer", "validation": {"min": 1, "max": 5}},
    )

    assert validate_field_answer(field, 3) == 3
    with pytest.raises(InvalidFieldAnswerError, match="minimum"):
        validate_field_answer(field, 0)
    with pytest.raises(InvalidFieldAnswerError):
        validate_field_answer(field, "3")


def test_date_answer_normalizes_iso_text_and_enforces_bounds() -> None:
    field = _field(
        interaction={"kind": "date"},
        response={
            "type": "date",
            "validation": {"earliest": "2026-01-01", "latest": "2026-12-31"},
        },
    )

    assert validate_field_answer(field, "2026-08-10") == datetime.date(2026, 8, 10)
    with pytest.raises(InvalidFieldAnswerError, match="earlier"):
        validate_field_answer(field, "2025-12-31")


def test_single_choice_rejects_an_option_from_another_field() -> None:
    field = _field(
        interaction={
            "kind": "single_choice",
            "options": [
                {"id": "option_yes", "label": "Yes"},
                {"id": "option_no", "label": "No"},
            ],
        },
        response={"type": "choice"},
    )

    assert validate_field_answer(field, "option_yes") == "option_yes"
    with pytest.raises(InvalidFieldAnswerError, match="does not belong"):
        validate_field_answer(field, "option_other")


def test_multiple_choice_enforces_uniqueness_and_selection_count() -> None:
    field = _field(
        interaction={
            "kind": "multiple_choice",
            "options": [
                {"id": "option_one", "label": "One"},
                {"id": "option_two", "label": "Two"},
            ],
        },
        response={"type": "choice_set", "validation": {"min_selections": 1}},
    )

    assert validate_field_answer(field, ["option_one"]) == ["option_one"]
    with pytest.raises(InvalidFieldAnswerError, match="too few"):
        validate_field_answer(field, [])
    with pytest.raises(InvalidFieldAnswerError, match="same option"):
        validate_field_answer(field, ["option_one", "option_one"])


def test_slider_answer_enforces_range_and_step() -> None:
    field = _field(
        interaction={"kind": "slider", "min": 0, "max": 10, "step": 2},
        response={"type": "integer"},
    )

    assert validate_field_answer(field, 4) == 4
    with pytest.raises(InvalidFieldAnswerError, match="step"):
        validate_field_answer(field, 3)
