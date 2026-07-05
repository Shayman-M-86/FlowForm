"""Unit tests for the canonical per-family answer-value models.

Covers per-family valid/invalid round-trips, the family-directed
``parse_answer_value`` helper, and the int/float strict-mode edge cases.
"""

from __future__ import annotations

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


class TestParseAnswerValuePerFamily:
    def test_choice(self) -> None:
        result = parse_answer_value("choice", {"selected": ["o1", "o2"]})
        assert isinstance(result, ChoiceAnswerValue)
        assert result.selected == ["o1", "o2"]

    def test_field_short_text(self) -> None:
        result = parse_answer_value("field", {"field_type": "short_text", "text": "hi"})
        assert isinstance(result, ShortTextFieldAnswerValue)

    def test_field_date(self) -> None:
        result = parse_answer_value("field", {"field_type": "date", "date": "2026-06-18"})
        assert isinstance(result, DateFieldAnswerValue)

    def test_matching(self) -> None:
        result = parse_answer_value(
            "matching",
            {"pairs": [{"prompt_id": "p1", "match_id": "m1"}]},
        )
        assert isinstance(result, MatchingAnswerValue)

    def test_rating(self) -> None:
        result = parse_answer_value("rating", {"variant": "stars", "number": 4})
        assert isinstance(result, StarsRatingAnswerValue)


class TestParseAnswerValueRejectsMismatch:
    def test_choice_shape_under_field_family_raises(self) -> None:
        with pytest.raises(ValidationError):
            parse_answer_value("field", {"selected": ["o1"]})

    def test_unknown_family_raises_key_error(self) -> None:
        with pytest.raises(KeyError):
            parse_answer_value("nope", {"selected": ["o1"]})  # type: ignore[arg-type]


class TestStrictModeValidation:
    def test_choice_forbids_extra_keys(self) -> None:
        with pytest.raises(ValidationError):
            ChoiceAnswerValue.model_validate({"selected": ["o1"], "extra": 1})

    def test_choice_rejects_duplicate_options(self) -> None:
        with pytest.raises(ValidationError):
            ChoiceAnswerValue.model_validate({"selected": ["o1", "o1"]})

    def test_matching_rejects_duplicate_prompt_ids(self) -> None:
        with pytest.raises(ValidationError):
            MatchingAnswerValue.model_validate(
                {"pairs": [{"prompt_id": "p1", "match_id": "m1"}, {"prompt_id": "p1", "match_id": "m2"}]}
            )

    def test_date_rejects_bad_format(self) -> None:
        with pytest.raises(ValidationError):
            DateFieldAnswerValue.model_validate({"field_type": "date", "date": "18-06-2026"})


class TestNumberIntFloatStrictMode:
    """Both int and float must satisfy the number unions under strict mode."""

    def test_number_field_accepts_int(self) -> None:
        result = parse_answer_value("field", {"field_type": "number", "number": 1})
        assert isinstance(result, NumberFieldAnswerValue)
        assert result.number == 1

    def test_number_field_accepts_float(self) -> None:
        result = parse_answer_value("field", {"field_type": "number", "number": 1.5})
        assert isinstance(result, NumberFieldAnswerValue)
        assert result.number == 1.5

    def test_slider_rating_accepts_int(self) -> None:
        result = parse_answer_value("rating", {"variant": "slider", "number": 1})
        assert isinstance(result, SliderRatingAnswerValue)

    def test_slider_rating_accepts_float(self) -> None:
        result = parse_answer_value("rating", {"variant": "slider", "number": 1.5})
        assert isinstance(result, SliderRatingAnswerValue)

    def test_emoji_rating_rejects_float(self) -> None:
        with pytest.raises(ValidationError):
            EmojiRatingAnswerValue.model_validate({"variant": "emoji", "number": 1.5})
