from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

# ----------------------------------------------------------
# Application errors
# ----------------------------------------------------------


class ApplicationError(Exception):
    """Base class for application-level errors."""

    description = "An application error occurred."


class InitializationError(Exception):
    """Error raised when the application fails to initialize correctly."""

    description = "An initialization error occurred."


class ConfigError(Exception):
    """Error raised when application configuration is invalid or missing."""

    description = "A configuration error occurred."


# ----------------------------------------------------------
# API-surface error base classes
#
# Concrete subclasses live in their respective layers:
#   - app/domain/errors.py        domain rule violations
#   - app/middleware/auth/...     auth middleware errors built from auth_errors.py
#   - app/middleware/rate_limit/  rate-limit errors
# ----------------------------------------------------------


@dataclass(slots=True)
class AppError(Exception):
    """Base class for domain-specific errors that can be returned in API responses.

    Attributes:
        status_code: HTTP status code to return for this error.
        code: Application-specific error code string.
        message: Human-readable error message.
        details: Optional dictionary of additional error details.
    """

    status_code: int
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class AuthError(AppError):
    """Base auth error that flows through the normal AppError handler.

    Carries an optional ``headers`` dict (e.g. ``WWW-Authenticate``) that the
    error handler attaches to the response.
    """

    def __init__(
        self,
        *,
        message: str,
        code: str,
        status_code: int = 401,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code, details=details or {})
        self.headers = headers or {}


class RequestValidationError(Exception):
    """The client request does not satisfy the endpoint schema."""

    def __init__(self, original_error: ValidationError) -> None:
        super().__init__("Request validation failed")
        self.original_error = original_error


class ResponseValidationError(Exception):
    """Server-side data does not satisfy the declared response schema."""

    def __init__(
        self,
        *,
        schema_name: str,
        original_error: ValidationError,
    ) -> None:
        super().__init__(f"Response validation failed for {schema_name}")
        self.schema_name = schema_name
        self.original_error = original_error
