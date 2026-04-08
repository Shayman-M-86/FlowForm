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
# Domain errors
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


class SurveyNotFoundError(AppError):
    """Error raised when a requested survey is not found in the database."""

    def __init__(self, survey_id: int, project_id: int) -> None:
        super().__init__(
            status_code=404,
            code="SURVEY_NOT_FOUND",
            message=f"Survey {survey_id} was not found in project {project_id}.",
        )


class PermissionDeniedError(AppError):
    """Error raised when a user attempts to perform an action they do not have permission for."""

    def __init__(self, message: str = "Permission denied.") -> None:
        super().__init__(
            status_code=403,
            code="FORBIDDEN",
            message=message,
        )


class SurveyPublishError(AppError):
    """Error raised when a survey cannot be published due to validation issues."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=409,
            code="SURVEY_PUBLISH_ERROR",
            message=message,
        )


# ----------------------------------------------------------
# API errors
# ----------------------------------------------------------
class ParsingValidationError(ValidationError):
    """Error raised when parsing validation fails."""

    description = "A parsing validation error occurred."


class RateLimitExceededError(AppError):
    """Error raised when a user exceeds the allowed rate limit."""

    def __init__(self, retry_after_seconds: int | None = None) -> None:
        super().__init__(
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded. Please retry after {retry_after_seconds} seconds."
            if retry_after_seconds is not None
            else "Rate limit exceeded. Please retry after some time.",
        )
        self.retry_after_seconds = retry_after_seconds
