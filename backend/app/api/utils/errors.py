from __future__ import annotations

import logging

from flask import Flask, jsonify
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from app.api.utils.validation import normalize_pydantic_errors
from app.core.errors import AppError, AuthError
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    """Register JSON API error handlers for the Flask application.

    The registered handlers convert exceptions into consistent JSON
    responses:

    - ``AppError`` returns ``code``, ``message``, and ``details`` using
      the exception's ``status_code``.
    - ``ValidationError`` returns a ``422`` response with a
      ``VALIDATION_ERROR`` code, a fixed message, and normalized
      validation ``errors``.
    - ``HTTPException`` returns a response with a ``code`` derived from
      the HTTP status (for example, ``HTTP_404``) and the exception
      description as the message.
    - Any other ``Exception`` is logged and transformed into a generic
      ``500 INTERNAL_SERVER_ERROR`` response.
    """
    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        return (
            jsonify(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            ),
            exc.status_code,
        )


    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        return (
            jsonify(
                {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "errors": normalize_pydantic_errors(exc),
                }
            ),
            422,
        )


    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        response = jsonify(
            {
                "code": f"HTTP_{exc.code}",
                "message": exc.description,
            }
        )
        response.status_code = exc.code or 500
        return response


    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        return (
            jsonify(
                {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                }
            ),
            500,
        )


    @app.errorhandler(AuthError)
    def handle_auth_error(exc: AuthError):
        response = jsonify(
            {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        )
        response.status_code = exc.status_code or 401
        for header_name, header_value in exc.headers.items():
            response.headers[header_name] = header_value
        return response
    
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(exc: IntegrityError):
        logger.error(f"Database integrity error: {exc}")
        response = jsonify(
                {
                    "code": "UNHANDLED_INTEGRITY_ERROR",
                    "message": "A database integrity error occurred.",
                }
            )
        response.status_code = 409
        return response