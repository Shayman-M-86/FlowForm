from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schema.api.requests.submissions.answers import AnswerIn


class SubmissionBaseRequest(BaseModel):
    """Base request body for survey submissions, containing common fields."""
    is_anonymous: bool = False
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    answers: list[AnswerIn] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateSubmissionRequest(SubmissionBaseRequest):
    """Request body for creating a new survey submission."""
    survey_version_id: int
    submitted_by_user_id: int | None = None  # remove once auth is in place


class PublicSubmissionRequest(SubmissionBaseRequest):
    """Request body for creating a new public survey submission."""
    public_token: str
    survey_version_id: int
