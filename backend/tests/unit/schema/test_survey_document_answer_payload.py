"""Strict scalar contracts used when reading and writing document answers."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schema.api.content.survey_document import parse_survey_document_answer_value


@pytest.mark.parametrize(
    "response_type,value,expected",
    [
        ("string", "hello", "hello"),
        ("integer", 3, 3),
        ("decimal", 3, 3),
        ("decimal", 3.5, 3.5),
        ("date", "2026-10-21", date(2026, 10, 21)),
        ("choice", "option_yes", "option_yes"),
        ("choice_set", ["option_yes", "option_no"], ["option_yes", "option_no"]),
    ],
)
def test_answer_value_round_trip(response_type, value, expected) -> None:
    assert parse_survey_document_answer_value(response_type, value) == expected


@pytest.mark.parametrize(
    "response_type,value",
    [
        ("integer", True),
        ("integer", 3.5),
        ("integer", "3"),
        ("decimal", True),
        ("decimal", "3.5"),
        ("decimal", float("nan")),
        ("decimal", float("inf")),
        ("date", "not-a-date"),
        ("date", 42),
        ("choice", "missing_prefix"),
        ("choice_set", ["missing_prefix"]),
        ("string", {"text": "old answer shape"}),
    ],
)
def test_answer_value_rejects_invalid_shape(response_type, value) -> None:
    with pytest.raises(ValidationError):
        parse_survey_document_answer_value(response_type, value)
