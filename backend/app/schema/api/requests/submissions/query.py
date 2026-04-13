from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SubmissionStatus = Literal["pending", "stored", "failed"]
SubmissionChannel = Literal["link", "slug", "system"]


class ListSubmissionsRequest(BaseModel):
    """Request body for partially updating a public share link."""
    survey_id: int | None = None
    status: SubmissionStatus | None = None
    submission_channel: SubmissionChannel | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class GetSubmissionRequest(BaseModel):
    """Request body for retrieving a specific submission by ID."""
    include_answers: bool = False
    resolve_identity: bool = False
