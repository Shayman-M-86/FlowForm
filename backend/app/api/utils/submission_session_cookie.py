from __future__ import annotations

from flask import Response, after_this_request

_SUBMISSION_SESSION_COOKIE = "flowform_submission_session"
_SUBMISSION_SESSION_COOKIE_PATH_PREFIX = "/api/v1/public/submission-session"
_SUBMISSION_SESSION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7


def set_submission_session_cookie(raw_token: str) -> None:
    """Attach the respondent session cookie to the current Flask response."""

    @after_this_request
    def _set_cookie(response: Response) -> Response:
        response.set_cookie(
            _SUBMISSION_SESSION_COOKIE,
            raw_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            path=_SUBMISSION_SESSION_COOKIE_PATH_PREFIX,
            max_age=_SUBMISSION_SESSION_COOKIE_MAX_AGE_SECONDS,
        )
        return response
