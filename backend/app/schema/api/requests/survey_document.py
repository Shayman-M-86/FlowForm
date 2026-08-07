"""Request contracts for answers submitted against canonical survey documents."""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator, model_validator

from app.schema.api.content.survey_document import (
    SurveyDocumentAnswerValue,
    parse_survey_document_answer_value,
)
from app.schema.enums import SubmissionAnswerState, SurveyResponseType


class SaveSurveyDocumentAnswerRequest(BaseModel):
    """Request body for saving or clearing one survey document field answer."""

    model_config = ConfigDict(extra="forbid")

    client_mutation_id: UUID
    response_type: SurveyResponseType
    state: SubmissionAnswerState
    value: SurveyDocumentAnswerValue | None = None

    @field_validator("value", mode="before")
    @classmethod
    def validate_value_for_response_type(cls, value: object, info: ValidationInfo) -> object:
        if value is None:
            return None
        response_type = info.data.get("response_type")
        if response_type is None:
            return value
        return parse_survey_document_answer_value(response_type, value)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state == "answered" and self.value is None:
            raise ValueError("value is required when state is 'answered'.")
        if self.state == "cleared" and self.value is not None:
            raise ValueError("value must be omitted when state is 'cleared'.")
        return self
