"""Request contracts for answers submitted against canonical survey documents."""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.schema.api.content.survey_document import (
    SurveyDocumentAnswerValue,
)
from app.schema.enums import SubmissionAnswerState


class SaveSurveyDocumentAnswerRequest(BaseModel):
    """Request body for saving or clearing one survey document field answer."""

    # The request only validates the transport envelope. Its field-specific
    # value type and constraints come from the resolved SurveyField.response.
    model_config = ConfigDict(extra="forbid")

    client_mutation_id: UUID
    state: SubmissionAnswerState
    value: SurveyDocumentAnswerValue | None = None

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state == "answered" and self.value is None:
            raise ValueError("value is required when state is 'answered'.")
        if self.state == "cleared" and self.value is not None:
            raise ValueError("value must be omitted when state is 'cleared'.")
        return self
