from __future__ import annotations

from pydantic import ConfigDict, Field

from app.schema.api.common.base import APIResponseModel
from app.schema.api.common.types import PageItems
from app.schema.enums import (
    SubmissionSessionStatus,
)
from app.schema.models.results.answer_results import AnswerSlotResult, SessionEventResult
from app.schema.types import (
    AnswerList,
    Count,
    PageNumber,
    PageSize,
    SubjectCode,
    SubjectId,
    SubmissionSessionId,
    SurveyId,
    SurveyVersionId,
    Timestamp,
)


class SurveySessionResponses(APIResponseModel):
    """Admin-facing summary of one respondent submission session.

    Sourced from core session metadata only; carries no decrypted answer
    payloads and no response-database locators or crypto material.
    """

    model_config = ConfigDict(from_attributes=True)

    session_id: SubmissionSessionId = Field(validation_alias="id")
    survey_id: SurveyId
    survey_version_id: SurveyVersionId
    status: SubmissionSessionStatus = Field(validation_alias="session_status")
    started_at: Timestamp
    completed_at: Timestamp | None = None
    last_activity_at: Timestamp


class SurveyAnswerSlotResponses(APIResponseModel, AnswerSlotResult):
    """HTTP representation of the shared AnswerSlotResult projection."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class SurveySessionEventResponses(APIResponseModel, SessionEventResult):
    """HTTP representation of the shared SessionEventResult projection."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class SurveySessionTreeResponses(APIResponseModel):
    """One session with its answer slots and optional event timeline."""

    model_config = ConfigDict(from_attributes=True)

    session: SurveySessionResponses
    answers: AnswerList[SurveyAnswerSlotResponses]
    events: list[SurveySessionEventResponses] | None = None


class SurveySubjectResponses(APIResponseModel):
    """Admin-facing summary of one project subject."""

    model_config = ConfigDict(from_attributes=True)

    subject_id: SubjectId = Field(validation_alias="id")
    subject_code: SubjectCode


class SurveySubjectTreeResponses(APIResponseModel):
    """One subject with all of its sessions for a survey."""

    model_config = ConfigDict(from_attributes=True)

    subject: SurveySubjectResponses
    sessions: list[SurveySessionTreeResponses]


class PaginatedSurveySubjectTreesResponses(APIResponseModel):
    """Paginated list of subject result trees."""

    items: PageItems[SurveySubjectTreeResponses]
    total: Count
    page: PageNumber
    page_size: PageSize
    include_decrypted_answer_values: bool
