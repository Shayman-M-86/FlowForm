from pydantic import BaseModel, ConfigDict, Field

from app.schema.api import limits
from app.schema.api.common.fields import NormalisedEmail, SubjectCode


class ListParticipantsQuery(BaseModel):
    """Query params for listing a project's participants."""

    model_config = ConfigDict(extra="forbid")

    search: str | None = None
    page: int = Field(default=limits.LIST_PAGE_DEFAULT, ge=limits.LIST_PAGE_MIN)
    page_size: int = Field(
        default=limits.LIST_PAGE_SIZE_DEFAULT,
        ge=limits.LIST_PAGE_SIZE_MIN,
        le=limits.LIST_PAGE_SIZE_MAX,
    )


class CreateParticipantRequest(BaseModel):
    """Request body for creating a participant (subject + email identity + participant)."""

    email: NormalisedEmail
    subject_code: SubjectCode | None = None


class UpdateParticipantRequest(BaseModel):
    """Request body for updating a participant's assigned email and/or subject code."""

    email: NormalisedEmail | None = None
    subject_code: SubjectCode | None = None
