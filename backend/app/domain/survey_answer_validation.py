"""Pure single-answer validation against a frozen question definition.

This module has one responsibility: validate one submitted answer value against
one frozen question definition from the compiled survey schema. It does not
load or inspect other answers, evaluate rule nodes, calculate visibility, or
perform completion-time validation.
"""
from __future__ import annotations

from typing import Any

from app.domain.errors import CompletionValidationError
from app.schema.api.submission_sessions import parse_answer_value
from app.schema.enums import AnswerFamily

KNOWN_FAMILIES: frozenset[str] = frozenset(AnswerFamily.__args__)  # type: ignore[attr-defined]


def validate_answer(question_definition: dict[str, Any], answer_value: Any) -> None:
    """Validate one answer against one frozen question definition.

    Validation happens in two stages:
    1. Validate the answer value against the canonical family payload model.
    2. Validate the parsed value against the exact question definition.
    """
    family = question_definition.get("family")
    parsed = _parse_known_family_answer(family, answer_value)
    if parsed is None:
        return

    definition = _definition_for(question_definition)

    try:
        parsed_value = parsed.model_dump()
        if family == "choice":
            _validate_choice_against_definition(parsed_value, definition)
        elif family == "field":
            _validate_field_against_definition(parsed_value, definition)
        elif family == "matching":
            _validate_matching_against_definition(parsed_value, definition)
        elif family == "rating":
            _validate_rating_against_definition(parsed_value, definition)
    except CompletionValidationError:
        raise
    except Exception as exc:
        raise CompletionValidationError(
            "Answer value is not valid for this question definition."
        ) from exc


def validate_answer_shape(family: str | None, answer_value: Any) -> None:
    """Validate a single answer value against its canonical family shape."""
    _parse_known_family_answer(family, answer_value)


def _parse_known_family_answer(family: str | None, answer_value: Any) -> Any | None:
    if family is None or family not in KNOWN_FAMILIES:
        return None
    try:
        return parse_answer_value(family, answer_value)  # type: ignore[arg-type]
    except Exception as exc:
        raise CompletionValidationError(
            f"Answer value does not match the '{family}' schema: {exc}"
        ) from exc


def _definition_for(question_definition: dict[str, Any]) -> dict[str, Any]:
    raw_definition = question_definition.get("definition")
    if isinstance(raw_definition, dict):
        return raw_definition

    # Older frozen schemas stored field metadata under ``field.schema``.
    raw_field = question_definition.get("field")
    if isinstance(raw_field, dict) and isinstance(raw_field.get("schema"), dict):
        return raw_field["schema"]

    return {}


def _validate_choice_against_definition(
    value: dict[str, Any], definition: dict[str, Any]
) -> None:
    selected = value.get("selected", [])
    option_ids = {
        option.get("id")
        for option in definition.get("options", [])
        if isinstance(option, dict)
    }
    if option_ids and any(option_id not in option_ids for option_id in selected):
        raise CompletionValidationError(
            "Choice answer includes an option that is not in this question."
        )

    min_selected = definition.get("min")
    max_selected = definition.get("max")
    if min_selected is not None and len(selected) < min_selected:
        raise CompletionValidationError(
            "Choice answer selects too few options for this question."
        )
    if max_selected is not None and len(selected) > max_selected:
        raise CompletionValidationError(
            "Choice answer selects too many options for this question."
        )


def _validate_field_against_definition(
    value: dict[str, Any], definition: dict[str, Any]
) -> None:
    expected_type = definition.get("field_type")
    if expected_type is not None and value.get("field_type") != expected_type:
        raise CompletionValidationError(
            "Field answer type does not match this question."
        )


def _validate_matching_against_definition(
    value: dict[str, Any], definition: dict[str, Any]
) -> None:
    prompt_ids = {
        item.get("id")
        for item in definition.get("prompts", [])
        if isinstance(item, dict)
    }
    match_ids = {
        item.get("id")
        for item in definition.get("matches", [])
        if isinstance(item, dict)
    }
    for pair in value.get("pairs", []):
        if prompt_ids and pair.get("prompt_id") not in prompt_ids:
            raise CompletionValidationError(
                "Matching answer includes a prompt that is not in this question."
            )
        if match_ids and pair.get("match_id") not in match_ids:
            raise CompletionValidationError(
                "Matching answer includes a match that is not in this question."
            )


def _validate_rating_against_definition(
    value: dict[str, Any], definition: dict[str, Any]
) -> None:
    variant = value.get("variant")
    if definition.get("variant") is not None and variant != definition.get("variant"):
        raise CompletionValidationError(
            "Rating answer variant does not match this question."
        )

    number = value.get("number")
    if not isinstance(number, int | float):
        raise CompletionValidationError(
            "Rating answer number is missing or invalid for this question."
        )
    if variant == "slider":
        _validate_slider_rating(number, definition)
    elif variant == "stars":
        _validate_star_rating(number, definition)
    elif variant == "emoji":
        _validate_emoji_rating(number)


def _validate_slider_rating(number: int | float, definition: dict[str, Any]) -> None:
    rating_range = definition.get("range", {})
    if not isinstance(rating_range, dict):
        rating_range = {}

    min_value = rating_range.get("min")
    max_value = rating_range.get("max")
    step = rating_range.get("step")
    if min_value is not None and number < min_value:
        raise CompletionValidationError("Rating answer is below this question's range.")
    if max_value is not None and number > max_value:
        raise CompletionValidationError("Rating answer is above this question's range.")
    if step is not None and min_value is not None:
        offset = (number - min_value) / step
        if abs(offset - round(offset)) > 1e-9:
            raise CompletionValidationError(
                "Rating answer does not align with this question's step."
            )


def _validate_star_rating(number: int | float, definition: dict[str, Any]) -> None:
    stars = definition.get("stars")
    if number < 1 or (stars is not None and number > stars):
        raise CompletionValidationError(
            "Star rating answer is outside this question's range."
        )


def _validate_emoji_rating(number: int | float) -> None:
    if number < 1 or number > 5:
        raise CompletionValidationError(
            "Emoji rating answer is outside this question's range."
        )
