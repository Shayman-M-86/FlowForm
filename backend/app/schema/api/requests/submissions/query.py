from __future__ import annotations

from pydantic import BaseModel, Field

from app.schema.api import limits
from app.schema.api.enums import SubmissionChannel, SubmissionStatus


class ListSubmissionsRequest(BaseModel):
    """Request body for partially updating a public share link."""
    survey_id: int | None = None
    status: SubmissionStatus | None = None
    submission_channel: SubmissionChannel | None = None
    page: int = Field(default=limits.LIST_PAGE_DEFAULT, ge=limits.LIST_PAGE_MIN)
    page_size: int = Field(
        default=limits.LIST_PAGE_SIZE_DEFAULT,
        ge=limits.LIST_PAGE_SIZE_MIN,
        le=limits.LIST_PAGE_SIZE_MAX,
    )


class GetSubmissionRequest(BaseModel):
    """Request body for retrieving a specific submission by ID."""
    include_answers: bool = False
    resolve_identity: bool = False
