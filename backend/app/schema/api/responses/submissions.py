from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schema.api import limits
from app.schema.api.enums import (
    AnswerFamily,
    SubmissionChannel,
    SubmissionStatus,
)


class AnswerOut(BaseModel):
    """API response shape for a single submission answer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_key: str
    answer_family: AnswerFamily
    answer_value: dict
    created_at: datetime


class SubmitterOut(BaseModel):
    """Lightweight submission submitter identity."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str | None


class CoreSubmissionOut(BaseModel):
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
    submitter: SubmitterOut | None = None
    is_anonymous: bool
    status: SubmissionStatus
    started_at: datetime | None
    submitted_at: datetime | None
    created_at: datetime


class LinkedSubmissionOut(BaseModel):
    """API response shape combining a core submission record with its answers."""

    model_config = ConfigDict(from_attributes=True)

    core: CoreSubmissionOut
    answers: list[AnswerOut] = Field(max_length=limits.ANSWER_LIST_ITEMS_MAX)


class PaginatedSubmissionsOut(BaseModel):
    """API response shape for a paginated list of submissions."""

    items: list[CoreSubmissionOut] = Field(max_length=limits.LIST_PAGE_SIZE_MAX)
    total: int
    page: int
    page_size: int
