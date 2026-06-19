"""Unit tests for pure single-answer survey validation."""
from __future__ import annotations

import pytest

from app.domain.errors import CompletionValidationError
from app.domain.survey_answer_validation import validate_answer, validate_answer_shape


class TestAnswerShapeValidation:
    def test_valid_choice_shape(self):
        validate_answer_shape("choice", {"selected": ["opt1"]})

    def test_invalid_choice_shape(self):
        with pytest.raises(CompletionValidationError, match="choice"):
            validate_answer_shape("choice", {"wrong": "shape"})

    def test_unknown_family_passes(self):
        validate_answer_shape("unknown_family", {"anything": True})

    def test_none_family_passes(self):
        validate_answer_shape(None, {"anything": True})


class TestSingleAnswerValidation:
    def test_choice_rejects_unknown_option(self):
        question = {
            "family": "choice",
            "definition": {
                "min": 1,
                "max": 2,
                "options": [
                    {"id": "opt1", "label": "One"},
                    {"id": "opt2", "label": "Two"},
                ],
            },
        }
        with pytest.raises(CompletionValidationError, match="not in this question"):
            validate_answer(question, {"selected": ["missing"]})

    def test_choice_rejects_too_many_options(self):
        question = {
            "family": "choice",
            "definition": {
                "min": 1,
                "max": 1,
                "options": [
                    {"id": "opt1", "label": "One"},
                    {"id": "opt2", "label": "Two"},
                ],
            },
        }
        with pytest.raises(CompletionValidationError, match="too many"):
            validate_answer(question, {"selected": ["opt1", "opt2"]})

    def test_field_rejects_wrong_field_type(self):
        question = {"family": "field", "definition": {"field_type": "email"}}
        with pytest.raises(CompletionValidationError, match="type does not match"):
            validate_answer(question, {"field_type": "short_text", "text": "hello"})

    def test_matching_rejects_unknown_prompt_or_match(self):
        question = {
            "family": "matching",
            "definition": {
                "prompts": [{"id": "p1", "label": "Prompt"}],
                "matches": [{"id": "m1", "label": "Match"}],
            },
        }
        with pytest.raises(CompletionValidationError, match="match"):
            validate_answer(question, {"pairs": [{"prompt_id": "p1", "match_id": "bad"}]})

    def test_rating_rejects_wrong_variant(self):
        question = {
            "family": "rating",
            "definition": {"variant": "stars", "stars": 5},
        }
        with pytest.raises(CompletionValidationError, match="variant"):
            validate_answer(question, {"variant": "slider", "number": 3})

    def test_rating_rejects_outside_slider_range(self):
        question = {
            "family": "rating",
            "definition": {
                "variant": "slider",
                "range": {"min": 0, "max": 10, "step": 1},
            },
        }
        with pytest.raises(CompletionValidationError, match="above"):
            validate_answer(question, {"variant": "slider", "number": 11})

    def test_valid_answer_passes(self):
        question = {
            "family": "field",
            "definition": {"field_type": "short_text"},
        }
        validate_answer(question, {"field_type": "short_text", "text": "hello"})
