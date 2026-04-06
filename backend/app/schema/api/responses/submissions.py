from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnswerOut(BaseModel):
    """API response shape for a single submission answer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_key: str
    answer_family: str
    answer_value: dict
    created_at: datetime


class CoreSubmissionOut(BaseModel):
    """API response shape for a core submission record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    survey_id: int
    survey_version_id: int
    response_store_id: int
    submission_channel: str
    submitted_by_user_id: int | None
    public_link_id: int | None
    is_anonymous: bool
    status: str
    started_at: datetime | None
    submitted_at: datetime | None
    created_at: datetime


class LinkedSubmissionOut(BaseModel):
    """API response shape combining a core submission record with its answers."""

    model_config = ConfigDict(from_attributes=True)

    core: CoreSubmissionOut
    answers: list[AnswerOut]

class ListSubmissionsRequest(BaseModel):
    """API request shape for listing submissions, supporting filtering by various criteria."""
    survey_id: int | None = None
    status: str | None = None
    submission_channel: str | None = None

class PaginatedSubmissionsOut(BaseModel):
    """API response shape for a paginated list of submissions."""
    items: list[CoreSubmissionOut]
    total: int
    page: int
    page_size: int
