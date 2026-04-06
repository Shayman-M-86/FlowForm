from datetime import datetime

from pydantic import BaseModel, Field


class AnswerIn(BaseModel):
    """A single answer payload within a submission."""

    question_key: str
    answer_family: str
    answer_value: dict


class CreateSubmissionRequest(BaseModel):
    """Request body for creating a new survey submission."""

    survey_version_id: int
    submitted_by_user_id: int | None = None  # TODO: replace with auth middleware
    is_anonymous: bool = False
    started_at: datetime
    submitted_at: datetime
    answers: list[AnswerIn] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class PublicSubmissionRequest(BaseModel):
    """Request body for submitting a survey response via a public link token."""

    public_token: str
    survey_version_id: int
    is_anonymous: bool = False
    answers: list[AnswerIn] = []
    metadata: dict | None = None
    started_at: datetime | None = None
    submitted_at: datetime | None = None


class ResolveTokenRequest(BaseModel):
    """Request body for resolving a public link token."""

    token: str

class ListSubmissionsRequest(BaseModel):
    """Request body for listing submissions, supporting filtering by various criteria."""
    survey_id: int | None = None
    status: str | None = None
    submission_channel: str | None = None
    
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class GetSubmissionRequest(BaseModel):
    """Request body for retrieving a specific submission by ID."""
    include_answers: bool = False
    resolve_identity: bool = False
