from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schema.api import limits

SurveyResponseSessionStatus = Literal["in_progress", "completed", "abandoned"]
SurveyResponseExportFormat = Literal["csv", "json"]


class ListSurveyResponsesRequest(BaseModel):
    """Query params for listing a survey's submission-session responses."""

    model_config = ConfigDict(extra="forbid")

    status: SurveyResponseSessionStatus | None = None
    page: int = Field(default=limits.LIST_PAGE_DEFAULT, ge=limits.LIST_PAGE_MIN)
    page_size: int = Field(
        default=limits.LIST_PAGE_SIZE_DEFAULT,
        ge=limits.LIST_PAGE_SIZE_MIN,
        le=limits.LIST_PAGE_SIZE_MAX,
    )


class ExportSurveyResponsesRequest(BaseModel):
    """Request body for exporting a survey's responses."""

    model_config = ConfigDict(extra="forbid")

    format: SurveyResponseExportFormat = "csv"
    include_history: bool = False
    session_ids: list[UUID] | None = Field(default=None, max_length=limits.LIST_PAGE_SIZE_MAX)
