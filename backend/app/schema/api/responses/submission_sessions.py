from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schema.enums import AnswerFamily, SubmissionAnswerState, SubmissionSessionStatus


class SubmissionSessionAnswerResponses(BaseModel):
    """Canonical latest answer state returned to a respondent."""

    question_node_id: UUID
    state: SubmissionAnswerState
    answer_family: AnswerFamily | None = None
    answer_value: dict[str, Any] | None = None
    revision_number: int
    client_mutation_id: UUID
    saved_at: datetime


class PublicSubmissionSessionResponses(BaseModel):
    """Session start/current acknowledgement without survey content or crypto material."""

    model_config = ConfigDict(from_attributes=True)

    status: SubmissionSessionStatus
    started_at: datetime
    expires_at: datetime
    survey_version_id: int


class CompleteSubmissionSessionResponses(BaseModel):
    """Response body for an idempotent respondent session completion."""

    status: Literal["completed"]
    completed_at: datetime
