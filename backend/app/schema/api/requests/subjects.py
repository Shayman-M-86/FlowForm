from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schema.api import limits
from app.schema.api.common.fields import SubjectCode


class ListSubjectsQuery(BaseModel):
    """Query params for listing a project's subjects."""

    model_config = ConfigDict(extra="forbid")

    canonical_status: Literal["canonical", "alias", "all"] = "canonical"
    is_participant: bool | None = None
    search: str | None = None
    page: int = Field(default=limits.LIST_PAGE_DEFAULT, ge=limits.LIST_PAGE_MIN)
    page_size: int = Field(
        default=limits.LIST_PAGE_SIZE_DEFAULT,
        ge=limits.LIST_PAGE_SIZE_MIN,
        le=limits.LIST_PAGE_SIZE_MAX,
    )


class UpdateSubjectRequest(BaseModel):
    """Request body for updating a subject's code."""

    subject_code: SubjectCode
