from __future__ import annotations

from app.schema import limits
from app.schema.api.common.base import APIRequestModel
from app.schema.api.common.types import PageNumber, PageSize, SessionIdList
from app.schema.enums import ExportFormat


class ListSubjectsRequest(APIRequestModel):
    """Query params for listing a survey's subjects with their session trees."""

    page: PageNumber = limits.LIST_PAGE_DEFAULT
    page_size: PageSize = limits.LIST_PAGE_SIZE_DEFAULT
    include_decrypted_answer_values: bool = False
    include_events: bool = False


class GetSubjectTreeRequest(APIRequestModel):
    """Query params for fetching one subject's full session tree."""

    include_decrypted_answer_values: bool = False
    include_events: bool = False


class ExportSurveyResultsRequest(APIRequestModel):
    """Request body for exporting a survey's results."""

    format: ExportFormat = "csv"
    include_decrypted_answer_values: bool = False
    session_ids: SessionIdList | None = None
