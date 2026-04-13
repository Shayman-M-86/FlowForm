from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schema.api.requests.submissions.answers import AnswerIn


class SubmissionBaseRequest(BaseModel):
    """Base request body for survey submissions, containing common fields."""

    started_at: datetime | None = None
    submitted_at: datetime | None = None
    answers: list[AnswerIn] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, value: list[AnswerIn]) -> list[AnswerIn]:
        if not value:
            raise ValueError("At least one answer is required.")
        return value

    @model_validator(mode="after")
    def validate_timestamps(self) -> SubmissionBaseRequest:
        if self.started_at and self.submitted_at and self.submitted_at < self.started_at:
            raise ValueError("submitted_at cannot be earlier than started_at.")
        return self


class LinkSubmissionRequest(SubmissionBaseRequest):
    """Request body for creating a survey submission from an authenticated link."""

    token: str
    survey_version_id: int

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("token must not be blank.")
        return value


class SlugSubmissionRequest(SubmissionBaseRequest):
    """Request body for creating a public-slug survey submission."""

    public_slug: str
    survey_version_id: int

    @field_validator("public_slug")
    @classmethod
    def validate_public_slug(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("public_slug must not be blank.")
        return value


PublicSubmissionRequest = LinkSubmissionRequest
AuthenticatedSubmissionRequest = LinkSubmissionRequest
