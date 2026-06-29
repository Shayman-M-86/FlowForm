from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator, model_validator

from app.schema.api.submission_sessions.answer_payload import (
    SubmissionAnswerValue,
    parse_answer_value,
)
from app.schema.enums import AnswerFamily, SubmissionAnswerState


class SaveSubmissionSessionAnswerRequest(BaseModel):
    """Request body for saving or clearing one respondent answer revision."""

    model_config = ConfigDict(extra="forbid")

    client_mutation_id: UUID
    state: SubmissionAnswerState
    answer_family: AnswerFamily | None = None
    answer_value: SubmissionAnswerValue | None = None

    @field_validator("answer_value", mode="before")
    @classmethod
    def validate_answer_value_matches_family(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        """Parse answer_value using answer_family when this is an answered request.

        The concrete per-family answer models live in answer_payload.py.
        This validator only delegates to that single source of truth.

        Request-level state rules are enforced in validate_answer_state().
        """
        if info.data.get("state") != "answered":
            return value

        answer_family = info.data.get("answer_family")
        if value is None or answer_family is None:
            return value

        return parse_answer_value(answer_family, value)

    @model_validator(mode="after")
    def validate_answer_state(self) -> Self:
        if self.state == "answered":
            if self.answer_family is None:
                raise ValueError("answer_family is required when state is 'answered'.")
            if self.answer_value is None:
                raise ValueError("answer_value is required when state is 'answered'.")
            return self

        if self.answer_family is not None:
            raise ValueError("answer_family must be omitted when state is 'cleared'.")
        if self.answer_value is not None:
            raise ValueError("answer_value must be omitted when state is 'cleared'.")
        return self