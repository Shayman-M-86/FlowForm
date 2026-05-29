from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schema.api import limits
from app.schema.api.enums import (
    AnswerFamily,
    SubmissionChannel,
    SubmissionStatus,
)


class AnswerResponses(BaseModel):
    """API response shape for a single submission answer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_key: str
    answer_family: AnswerFamily
    answer_value: dict
    created_at: datetime


class SubmitterResponses(BaseModel):
    """Lightweight submission submitter identity."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str | None


class CoreSubmissionResponses(BaseModel):
    """API response shape for a core submission record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    survey_id: int
    survey_version_id: int
    response_store_id: int
    submission_channel: SubmissionChannel
    submitted_by_user_id: int | None
    survey_link_id: int | None
    submitter: SubmitterResponses | None = None
    is_anonymous: bool
    status: SubmissionStatus
    started_at: datetime | None
    submitted_at: datetime | None
    created_at: datetime


class LinkedSubmissionResponses(BaseModel):
    """API response shape combining a core submission record with its answers."""

    model_config = ConfigDict(from_attributes=True)

    core: CoreSubmissionResponses
    answers: list[AnswerResponses] = Field(max_length=limits.ANSWER_LIST_ITEMS_MAX)


class PaginatedSubmissionsResponses(BaseModel):
    """API response shape for a paginated list of submissions."""

    items: list[CoreSubmissionResponses] = Field(max_length=limits.LIST_PAGE_SIZE_MAX)
    total: int
    page: int
    page_size: int
