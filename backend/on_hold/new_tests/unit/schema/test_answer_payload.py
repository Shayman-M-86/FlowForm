"""Unit tests for canonical respondent answer-value payloads."""

from __future__ import annotations

from typing import Any, cast

import pytest
from pydantic import ValidationError

from app.schema.api.submission_sessions.answer_payload import (
    ChoiceAnswerValue,
    DateFieldAnswerValue,
    EmojiRatingAnswerValue,
    MatchingAnswerValue,
    NumberFieldAnswerValue,
    ShortTextFieldAnswerValue,
    SliderRatingAnswerValue,
    StarsRatingAnswerValue,
    parse_answer_value,
)


def test_parse_answer_value_accepts_choice_family() -> None:
    """Choice answers parse to the canonical choice model."""
    result = parse_answer_value("choice", {"selected": ["option-1", "option-2"]})

    assert isinstance(result, ChoiceAnswerValue)
    assert result.selected == ["option-1", "option-2"]


def test_parse_answer_value_accepts_short_text_field() -> None:
    """Field answers parse through the field discriminator."""
    result = parse_answer_value("field", {"field_type": "short_text", "text": "hello"})

    assert isinstance(result, ShortTextFieldAnswerValue)
    assert result.text == "hello"


def test_parse_answer_value_accepts_date_field() -> None:
    """Date field answers keep the canonical YYYY-MM-DD shape."""
    result = parse_answer_value("field", {"field_type": "date", "date": "2026-06-18"})

    assert isinstance(result, DateFieldAnswerValue)
    assert result.date == "2026-06-18"


def test_parse_answer_value_accepts_matching_family() -> None:
    """Matching answers parse to prompt/match pairs."""
    result = parse_answer_value(
        "matching",
        {"pairs": [{"prompt_id": "prompt-1", "match_id": "match-1"}]},
    )

    assert isinstance(result, MatchingAnswerValue)
    assert result.pairs[0].prompt_id == "prompt-1"


def test_parse_answer_value_accepts_rating_family() -> None:
    """Rating answers parse through the rating discriminator."""
    result = parse_answer_value("rating", {"variant": "stars", "number": 4})

    assert isinstance(result, StarsRatingAnswerValue)
    assert result.number == 4


def test_parse_answer_value_rejects_family_shape_mismatch() -> None:
    """A payload from one family should not validate under another family."""
    with pytest.raises(ValidationError):
        parse_answer_value("field", {"selected": ["option-1"]})


def test_parse_answer_value_rejects_unknown_family() -> None:
    """Unknown answer families should fail before payload parsing."""
    with pytest.raises(KeyError):
        parse_answer_value(cast(Any, "nope"), {"selected": ["option-1"]})


def test_choice_answer_forbids_extra_keys() -> None:
    """Canonical answer payloads should reject unknown keys."""
    with pytest.raises(ValidationError):
        ChoiceAnswerValue.model_validate({"selected": ["option-1"], "extra": 1})


def test_choice_answer_rejects_duplicate_options() -> None:
    """A choice answer cannot select the same option twice."""
    with pytest.raises(ValidationError):
        ChoiceAnswerValue.model_validate({"selected": ["option-1", "option-1"]})


def test_matching_answer_rejects_duplicate_prompt_ids() -> None:
    """A matching answer cannot answer the same prompt twice."""
    with pytest.raises(ValidationError):
        MatchingAnswerValue.model_validate(
            {
                "pairs": [
                    {"prompt_id": "prompt-1", "match_id": "match-1"},
                    {"prompt_id": "prompt-1", "match_id": "match-2"},
                ]
            }
        )


def test_date_answer_rejects_bad_format() -> None:
    """Date answers must use the API date string format."""
    with pytest.raises(ValidationError):
        DateFieldAnswerValue.model_validate({"field_type": "date", "date": "18-06-2026"})


def test_number_field_accepts_int_and_float() -> None:
    """Number fields preserve both integer and decimal JSON numbers."""
    int_result = parse_answer_value("field", {"field_type": "number", "number": 1})
    float_result = parse_answer_value("field", {"field_type": "number", "number": 1.5})

    assert isinstance(int_result, NumberFieldAnswerValue)
    assert int_result.number == 1
    assert isinstance(float_result, NumberFieldAnswerValue)
    assert float_result.number == 1.5


def test_slider_rating_accepts_int_and_float() -> None:
    """Slider ratings preserve both integer and decimal JSON numbers."""
    int_result = parse_answer_value("rating", {"variant": "slider", "number": 1})
    float_result = parse_answer_value("rating", {"variant": "slider", "number": 1.5})

    assert isinstance(int_result, SliderRatingAnswerValue)
    assert isinstance(float_result, SliderRatingAnswerValue)


def test_emoji_rating_rejects_float() -> None:
    """Emoji ratings are discrete integer ratings."""
    with pytest.raises(ValidationError):
        EmojiRatingAnswerValue.model_validate({"variant": "emoji", "number": 1.5})
