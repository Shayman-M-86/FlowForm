from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schema.api import limits
from app.schema.enums import ExportFormat


class ListSubjectsRequest(BaseModel):
    """Query params for listing a survey's subjects with their session trees."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=limits.LIST_PAGE_DEFAULT, ge=limits.LIST_PAGE_MIN)
    page_size: int = Field(
        default=limits.LIST_PAGE_SIZE_DEFAULT,
        ge=limits.LIST_PAGE_SIZE_MIN,
        le=limits.LIST_PAGE_SIZE_MAX,
    )
    include_decrypted_answer_values: bool = False
    include_events: bool = False


class GetSubjectTreeRequest(BaseModel):
    """Query params for fetching one subject's full session tree."""

    model_config = ConfigDict(extra="forbid")

    include_decrypted_answer_values: bool = False
    include_events: bool = False


class ExportSurveyResultsRequest(BaseModel):
    """Request body for exporting a survey's results."""

    model_config = ConfigDict(extra="forbid")

    format: ExportFormat = "csv"
    include_decrypted_answer_values: bool = False
    session_ids: list[UUID] | None = Field(default=None, max_length=limits.LIST_PAGE_SIZE_MAX)
