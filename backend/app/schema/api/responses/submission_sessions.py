from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schema.api import limits
from app.schema.enums import AnswerFamily, SubmissionAnswerState, SubmissionSessionStatus


class PublicSubmissionSessionSurveyResponses(BaseModel):
    """Public survey summary returned with a respondent session."""

    id: int
    title: str


class PublicSubmissionSessionVersionResponses(BaseModel):
    """Published survey version frozen into a respondent session."""

    id: int
    version_number: int
    compiled_schema: dict[str, Any]


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
    """Public respondent session response without raw resume or crypto material."""

    model_config = ConfigDict(from_attributes=True)

    status: SubmissionSessionStatus
    started_at: datetime
    expires_at: datetime
    survey: PublicSubmissionSessionSurveyResponses
    version: PublicSubmissionSessionVersionResponses
    answers: list[SubmissionSessionAnswerResponses] = Field(max_length=limits.ANSWER_LIST_ITEMS_MAX)


class CompleteSubmissionSessionResponses(BaseModel):
    """Response body for an idempotent respondent session completion."""

    status: Literal["completed"]
    completed_at: datetime
