from __future__ import annotations

import logging
from typing import Any

from flask import Flask, jsonify
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.api.utils.validation import normalize_pydantic_errors
from app.core.errors import AppError, RequestValidationError, ResponseValidationError

logger = logging.getLogger(__name__)


def _error_response(
    *,
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
):
    """Build a consistent JSON error response.

    All API errors share the shape ``{code, message, details?}`` — ``details``
    is included only when non-empty so absence and emptiness are equivalent.
    Optional ``headers`` are attached to the response (used by 429 to carry
    ``Retry-After``, by 401 to carry ``WWW-Authenticate``, etc.).
    """
    payload: dict[str, Any] = {"code": code, "message": message}
    if details:
        payload["details"] = details

    response = jsonify(payload)
    response.status_code = status_code
    for name, value in (headers or {}).items():
        response.headers[name] = value
    return response


def register_error_handlers(app: Flask) -> None:
    """Register JSON API error handlers for the Flask application.

    Every handler produces the same top-level shape:

    .. code-block:: json

        {
            "code": "MACHINE_READABLE_CODE",
            "message": "Human-readable description.",
            "details": { /* optional, structured extras */ }
        }

    ``details`` is omitted when empty. Pydantic validation errors place their
    per-field error array under ``details.errors`` rather than at the top
    level, so clients only have to handle one shape.

    Status mapping:

    - ``AppError`` (and subclasses, including ``AuthError``,
      ``DbIntegrityError``, ``UnhandledDbIntegrityError``,
      ``RateLimitExceededError``) → uses ``exc.status_code``; honours any
      ``exc.headers`` if present.
    - ``ValidationError`` (Pydantic) → ``422`` with code ``VALIDATION_ERROR``
      and ``details.errors`` listing each field failure.
    - ``HTTPException`` (werkzeug) → uses ``exc.code``, response code is
      ``HTTP_<status>``.
    - ``IntegrityError`` that escaped ``commit_with_err_handle`` → ``500``
      with code ``UNHANDLED_DB_INTEGRITY_ERROR``.
    - Any other ``Exception`` → ``500`` with code ``INTERNAL_SERVER_ERROR``.
    """

    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        return _error_response(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            headers=getattr(exc, "headers", None),
        )


    @app.errorhandler(RequestValidationError)
    def handle_request_validation_error(exc: RequestValidationError):
        return _error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            status_code=422,
            details={
                "errors": normalize_pydantic_errors(
                    exc.original_error,
                ),
            },
        )


    @app.errorhandler(ResponseValidationError)
    def handle_response_validation_error(exc: ResponseValidationError):
        logger.exception(
            "Response validation failed for schema %s",
            exc.schema_name,
            exc_info=exc,
        )

        return _error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
            status_code=500,
        )


    @app.errorhandler(ValidationError)
    def handle_unclassified_validation_error(exc: ValidationError):
        logger.exception(
            "Unclassified Pydantic validation error",
            exc_info=exc,
        )

        return _error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
            status_code=500,
        )


    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        status = exc.code or 500
        return _error_response(
            code=f"HTTP_{status}",
            message=exc.description or "",
            status_code=status,
        )


    @app.errorhandler(IntegrityError)
    def handle_integrity_error(exc: IntegrityError):
        """Fallback for IntegrityErrors raised outside ``commit_with_err_handle``.

        Normal DB flows route through ``commit_with_err_handle`` /
        ``flush_with_err_handle``, which translate matched violations to
        ``DbIntegrityError`` (handled by ``handle_app_error``) and unmatched
        ones to ``UnhandledDbIntegrityError``. Reaching this handler means
        raw SQLAlchemy ``IntegrityError`` escaped those helpers entirely —
        a server bug.
        """
        logger.exception("Untranslated database integrity error", exc_info=exc)
        return _error_response(
            code="UNHANDLED_DB_INTEGRITY_ERROR",
            message="An unexpected database integrity error occurred.",
            status_code=500,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        return _error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
            status_code=500,
        )


