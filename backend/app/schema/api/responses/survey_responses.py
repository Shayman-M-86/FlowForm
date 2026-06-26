from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schema.api import limits
from app.schema.api.submission_sessions.answer_payload import SubmissionAnswerValue
from app.schema.enums import AnswerFamily, ExportFormat, SubmissionAnswerState, SubmissionSessionStatus


class SurveyResponseSummaryResponses(BaseModel):
    """Admin-facing summary of one respondent submission session.

    Sourced from core session metadata only; carries no decrypted answer
    payloads and no response-database locators or crypto material.
    """

    model_config = ConfigDict(from_attributes=True)

    session_id: UUID = Field(validation_alias="id")
    survey_id: int
    survey_version_id: int
    status: SubmissionSessionStatus = Field(validation_alias="session_status")
    started_at: datetime
    completed_at: datetime | None = None
    last_activity_at: datetime


class PaginatedSurveyResponsesResponses(BaseModel):
    """Paginated list of admin survey-response summaries."""

    items: list[SurveyResponseSummaryResponses] = Field(max_length=limits.LIST_PAGE_SIZE_MAX)
    total: int
    page: int
    page_size: int


class SurveyResponseAnswerResponses(BaseModel):
    """One decrypted canonical answer in an admin survey-response detail view."""

    model_config = ConfigDict(from_attributes=True)

    question_node_id: UUID
    state: SubmissionAnswerState = Field(validation_alias="answer_state")
    answer_family: AnswerFamily | None = None
    answer_value: SubmissionAnswerValue | dict[str, Any] | None = None


class SurveyResponseDetailResponses(BaseModel):
    """Admin survey-response detail: session metadata plus canonical decrypted answers."""

    model_config = ConfigDict(from_attributes=True)

    session: SurveyResponseSummaryResponses
    answers: list[SurveyResponseAnswerResponses] = Field(max_length=limits.ANSWER_LIST_ITEMS_MAX)


class SurveyResponseHistoryResponses(BaseModel):
    """Admin current-answer history-compatible view for a session."""

    model_config = ConfigDict(from_attributes=True)

    session: SurveyResponseSummaryResponses
    revisions: list[SurveyResponseAnswerResponses] = Field(max_length=limits.ANSWER_LIST_ITEMS_MAX)


class SurveyResponseExportResponses(BaseModel):
    """Result envelope for a survey-response export request."""

    format: ExportFormat
    include_history: bool
    session_count: int
    download_url: str | None = None
