from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flask import Response

from app.schema.api.responses.submission_sessions import (
    PublicSubmissionSessionResponses,
    PublicSubmissionSessionSurveyResponses,
    PublicSubmissionSessionVersionResponses,
)

_SUBMISSION_SESSION_COOKIE = "flowform_submission_session"
_PLACEHOLDER_COOKIE_VALUE = "phase2-placeholder"


def build_placeholder_session_response(*, now: datetime | None = None) -> PublicSubmissionSessionResponses:
    """Build the temporary Phase 2 public session response body.

    These routes are currently contract-first stubs: they need to validate and
    document the final public API shape before the real session service starts
    coordinating core and response database writes. This helper keeps that
    placeholder response in one place so the route handlers do not look like
    they are performing real session lookup, survey resolution, or answer
    hydration yet.
    """
    current = now or datetime.now(UTC)
    return PublicSubmissionSessionResponses(
        status="in_progress",
        started_at=current,
        expires_at=current + timedelta(days=7),
        survey=PublicSubmissionSessionSurveyResponses(id=1, title="Phase 2 placeholder survey"),
        version=PublicSubmissionSessionVersionResponses(id=1, version_number=1, compiled_schema={}),
        answers=[],
    )


def set_placeholder_submission_session_cookie(response: Response) -> Response:
    """Attach the temporary respondent resume cookie to a Flask response.

    The real implementation will mint, hash, store, and rotate an opaque
    browser resume token after the required core session and response envelope
    records exist. Until that service work lands, this helper only reserves the
    cookie name and security attributes expected by the public contract. The
    placeholder value must not be treated as authentication or persisted state.
    """
    response.set_cookie(
        _SUBMISSION_SESSION_COOKIE,
        _PLACEHOLDER_COOKIE_VALUE,
        httponly=True,
        secure=True,
        samesite="Lax",
        path="/api/v1/public/submission-sessions",
        max_age=60 * 60 * 24 * 7,
    )
    return response
