from __future__ import annotations

import logging

from flask import Flask, jsonify
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from app.api.utils.validation import normalize_pydantic_errors
from app.core.errors import AppError

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
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
