from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.schema.api.responses.survey_responses import (
    PaginatedSurveyResponsesResponses,
    SurveyResponseDetailResponses,
    SurveyResponseExportResponses,
    SurveyResponseHistoryResponses,
    SurveyResponseSummaryResponses,
)


def _placeholder_summary(
    survey_id: int, session_id: UUID, *, now: datetime | None = None
) -> SurveyResponseSummaryResponses:
    current = now or datetime.now(UTC)
    return SurveyResponseSummaryResponses(
        session_id=session_id,
        survey_id=survey_id,
        survey_version_id=1,
        status="completed",
        started_at=current - timedelta(minutes=5),
        completed_at=current,
        last_activity_at=current,
    )


def build_placeholder_response_list(*, page: int, page_size: int) -> PaginatedSurveyResponsesResponses:
    """Phase 2 admin survey-response list stub.

    Returns an empty page until the Phase 7 admin-read service lists real core
    session metadata. The shape is final so Studio can wire its results view.
    """
    return PaginatedSurveyResponsesResponses(items=[], total=0, page=page, page_size=page_size)


def build_placeholder_response_detail(survey_id: int, session_id: UUID) -> SurveyResponseDetailResponses:
    """Phase 2 admin survey-response detail stub with no decrypted answers yet."""
    return SurveyResponseDetailResponses(
        session=_placeholder_summary(survey_id, session_id),
        answers=[],
    )


def build_placeholder_response_history(survey_id: int, session_id: UUID) -> SurveyResponseHistoryResponses:
    """Phase 2 admin answer-history stub with no decrypted revisions yet."""
    return SurveyResponseHistoryResponses(
        session=_placeholder_summary(survey_id, session_id),
        revisions=[],
    )


def build_placeholder_response_export(
    *, export_format: str, include_history: bool, session_count: int
) -> SurveyResponseExportResponses:
    """Phase 2 admin export stub; no file is produced until Phase 7."""
    return SurveyResponseExportResponses(
        format="json" if export_format == "json" else "csv",
        include_history=include_history,
        session_count=session_count,
        download_url=None,
    )
