"""Validate one submitted value against its resolved survey document field."""

from __future__ import annotations

import datetime
import math
import re

from pydantic import EmailStr, HttpUrl, TypeAdapter, ValidationError

from app.domain.errors import InvalidFieldAnswerError
from app.schema.api.content.survey_document import (
    ChoiceInteraction,
    ChoiceSetResponse,
    ChoiceSetValidation,
    DateResponse,
    DateValidation,
    MultipleChoiceInteraction,
    NumberValidation,
    RatingInteraction,
    SingleChoiceInteraction,
    SliderInteraction,
    StringResponse,
    SurveyDocumentAnswerValue,
    SurveyField,
    parse_survey_document_answer_value,
)
from app.schema.enums import SurveyStringFormat

_EMAIL_ADAPTER = TypeAdapter(EmailStr)
_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)
_TELEPHONE_CHARACTERS = re.compile(r"^[0-9\s()+\-./xX#*]+$")


def validate_field_answer(field: SurveyField, raw_value: object) -> SurveyDocumentAnswerValue:
    """Return a normalized value after enforcing the field's exact contract."""
    try:
        value = parse_survey_document_answer_value(field.response.type, raw_value)
        _validate_response_constraints(field, value)
        _validate_interaction_constraints(field, value)
        return value
    except InvalidFieldAnswerError:
        raise
    except (ValidationError, TypeError, ValueError) as exc:
        raise InvalidFieldAnswerError() from exc


def _validate_response_constraints(field: SurveyField, value: SurveyDocumentAnswerValue) -> None:
    response = field.response
    validation = getattr(response, "validation", None)

    if isinstance(response, StringResponse) and isinstance(value, str) and validation is not None:
        if validation.min_length is not None and len(value) < validation.min_length:
            raise InvalidFieldAnswerError("Answer is shorter than this field allows.")
        if validation.max_length is not None and len(value) > validation.max_length:
            raise InvalidFieldAnswerError("Answer is longer than this field allows.")
        _validate_string_format(value, validation.format)

    if isinstance(validation, NumberValidation) and isinstance(value, int | float):
        if validation.min is not None and value < validation.min:
            raise InvalidFieldAnswerError("Answer is below this field's minimum.")
        if validation.max is not None and value > validation.max:
            raise InvalidFieldAnswerError("Answer is above this field's maximum.")

    if (
        isinstance(response, DateResponse)
        and isinstance(value, datetime.date)
        and isinstance(validation, DateValidation)
    ):
        if validation.earliest is not None and value < validation.earliest:
            raise InvalidFieldAnswerError("Answer is earlier than this field allows.")
        if validation.latest is not None and value > validation.latest:
            raise InvalidFieldAnswerError("Answer is later than this field allows.")

    if (
        isinstance(response, ChoiceSetResponse)
        and isinstance(value, list)
        and isinstance(validation, ChoiceSetValidation)
    ):
        if validation.min_selections is not None and len(value) < validation.min_selections:
            raise InvalidFieldAnswerError("Answer selects too few options.")
        if validation.max_selections is not None and len(value) > validation.max_selections:
            raise InvalidFieldAnswerError("Answer selects too many options.")


def _validate_string_format(value: str, answer_format: SurveyStringFormat | None) -> None:
    if answer_format == "email":
        _EMAIL_ADAPTER.validate_python(value)
    elif answer_format == "url":
        _HTTP_URL_ADAPTER.validate_python(value)
    elif answer_format == "tel" and (
        not _TELEPHONE_CHARACTERS.fullmatch(value) or not any(character.isdigit() for character in value)
    ):
        raise InvalidFieldAnswerError("Answer is not a valid telephone number.")


def _validate_interaction_constraints(field: SurveyField, value: SurveyDocumentAnswerValue) -> None:
    interaction = field.interaction

    if isinstance(interaction, ChoiceInteraction):
        selected = value if isinstance(value, list) else [value]
        option_ids = {option.id for option in interaction.options}
        if len(selected) != len(set(selected)):
            raise InvalidFieldAnswerError("Answer cannot select the same option more than once.")
        if any(option_id not in option_ids for option_id in selected):
            raise InvalidFieldAnswerError("Answer includes an option that does not belong to this field.")
        if isinstance(interaction, SingleChoiceInteraction) and len(selected) != 1:
            raise InvalidFieldAnswerError("Answer must select exactly one option.")
        if isinstance(interaction, MultipleChoiceInteraction) and not isinstance(value, list):
            raise InvalidFieldAnswerError("Answer must provide a list of selected options.")

    if (
        isinstance(interaction, RatingInteraction)
        and isinstance(value, int | float)
        and (value < interaction.min or value > interaction.max)
    ):
        raise InvalidFieldAnswerError("Answer is outside this rating's range.")

    if isinstance(interaction, SliderInteraction) and isinstance(value, int | float):
        if value < interaction.min or value > interaction.max:
            raise InvalidFieldAnswerError("Answer is outside this slider's range.")
        offset = (value - interaction.min) / interaction.step
        if not math.isclose(offset, round(offset), abs_tol=1e-9):
            raise InvalidFieldAnswerError("Answer does not align with this slider's step.")
