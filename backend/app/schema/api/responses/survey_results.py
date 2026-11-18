from __future__ import annotations

from pydantic import ConfigDict, Field

from app.schema import limits
from app.schema.api.common.base import APIResponseModel
from app.schema.api.common.types import PageItems, PageNumber, PageSize
from app.schema.enums import (
    SubmissionAnswerState,
    SubmissionEventType,
    SubmissionSessionStatus,
)
from app.schema.models.survey.answer_spec import AnswerSpec
from app.schema.models.survey.answer_value import AnswerValue
from app.schema.models.survey.fields import SurveyField
from app.schema.types import (
    AnswerList,
    Count,
    ReadableId,
    SubjectCode,
    SubjectId,
    SubmissionSessionId,
    SurveyFieldUuid,
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


class SurveyAnswerSlotResponses(APIResponseModel):
    """One answer slot in an admin survey-results view, optionally decrypted."""

    model_config = ConfigDict(from_attributes=True, str_max_length=limits.LONG_STRING_MAX)

    field_uuid: SurveyFieldUuid
    field_id: ReadableId | None = None
    answer_spec: AnswerSpec | None = None
    has_encrypted_answer: bool
    decrypted: bool
    state: SubmissionAnswerState | None = Field(default=None, validation_alias="answer_state")
    answer_value: AnswerValue | None = None
    field: SurveyField | None = None


class SurveySessionEventResponses(APIResponseModel):
    """One timeline event for a session. Never carries answer values."""

    model_config = ConfigDict(from_attributes=True)

    event_type: SubmissionEventType
    field_uuid: SurveyFieldUuid | None = None
    received_at: Timestamp


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
