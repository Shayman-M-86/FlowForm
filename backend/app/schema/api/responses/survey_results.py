from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schema.api import limits
from app.schema.api.submission_sessions.answer_payload import SubmissionAnswerValue
from app.schema.enums import (
    AnswerFamily,
    SubmissionAnswerState,
    SubmissionEventType,
    SubmissionSessionStatus,
)


class SurveySessionResponses(BaseModel):
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


class SurveyAnswerSlotResponses(BaseModel):
    """One answer slot in an admin survey-results view, optionally decrypted."""

    model_config = ConfigDict(from_attributes=True)

    question_node_id: UUID
    question_key: str | None = None
    answer_family: AnswerFamily | None = None
    has_encrypted_answer: bool
    decrypted: bool
    state: SubmissionAnswerState | None = Field(default=None, validation_alias="answer_state")
    answer_value: SubmissionAnswerValue | dict[str, Any] | None = None


class SurveySessionEventResponses(BaseModel):
    """One timeline event for a session. Never carries answer values."""

    model_config = ConfigDict(from_attributes=True)

    event_type: SubmissionEventType
    question_node_id: UUID | None = None
    received_at: datetime


class SurveySessionTreeResponses(BaseModel):
    """One session with its answer slots and optional event timeline."""

    model_config = ConfigDict(from_attributes=True)

    session: SurveySessionResponses
    answers: list[SurveyAnswerSlotResponses] = Field(max_length=limits.ANSWER_LIST_ITEMS_MAX)
    events: list[SurveySessionEventResponses] | None = None


class SurveySubjectResponses(BaseModel):
    """Admin-facing summary of one project subject."""

    model_config = ConfigDict(from_attributes=True)

    subject_id: UUID = Field(validation_alias="id")
    subject_code: str


class SurveySubjectTreeResponses(BaseModel):
    """One subject with all of its sessions for a survey."""

    model_config = ConfigDict(from_attributes=True)

    subject: SurveySubjectResponses
    sessions: list[SurveySessionTreeResponses]


class PaginatedSurveySubjectTreesResponses(BaseModel):
    """Paginated list of subject result trees."""

    items: list[SurveySubjectTreeResponses] = Field(max_length=limits.LIST_PAGE_SIZE_MAX)
    total: int
    page: int
    page_size: int
    include_decrypted_answer_values: bool
