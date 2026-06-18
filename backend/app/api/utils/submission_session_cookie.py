from __future__ import annotations

from flask import Response, after_this_request, request

_SUBMISSION_SESSION_COOKIE = "flowform_submission_session"
_SUBMISSION_SESSION_COOKIE_PATH_PREFIX = "/api/v1/respondent/submission-sessions"
_SUBMISSION_SESSION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7

# Recognition token: a returning-browser cookie scoped to the whole public area,
# not just one submission session. Lives much longer than the session cookie.
_RECOGNITION_COOKIE = "flowform_subject_recognition"
_RECOGNITION_COOKIE_PATH = "/api/v1/respondent"
_RECOGNITION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365


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


def get_recognition_token() -> str | None:
    """Read the recognition token from the incoming request cookie, if present."""
    return request.cookies.get(_RECOGNITION_COOKIE)


def set_recognition_cookie(raw_token: str) -> None:
    """Attach the returning-browser recognition cookie to the current Flask response."""

    @after_this_request
    def _set_cookie(response: Response) -> Response:
        response.set_cookie(
            _RECOGNITION_COOKIE,
            raw_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            path=_RECOGNITION_COOKIE_PATH,
            max_age=_RECOGNITION_COOKIE_MAX_AGE_SECONDS,
        )
        return response
