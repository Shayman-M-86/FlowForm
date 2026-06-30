"""Custom exceptions for the email service.

These exceptions keep the rest of the application from depending directly on
Jinja or boto3 error types.  They extend ``AppError`` so the global error
handler produces the same ``{code, message, details}`` JSON shape used by
domain errors.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import AppError


class EmailServiceError(AppError):
    """Base error for all email service failures."""

    def __init__(
        self,
        message: str = "An email service error occurred.",
        *,
        status_code: int = 502,
        code: str = "EMAIL_SERVICE_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            code=code,
            message=message,
            details=details or {},
        )


class EmailConfigError(EmailServiceError):
    """Raised when the email service is missing required configuration."""

    def __init__(self, message: str = "Email service configuration error.") -> None:
        super().__init__(message, status_code=500, code="EMAIL_CONFIG_ERROR")


class EmailRenderError(EmailServiceError):
    """Raised when an email template cannot be rendered."""

    def __init__(self, message: str = "Failed to render email template.") -> None:
        super().__init__(message, status_code=500, code="EMAIL_RENDER_ERROR")


class EmailTemplateNotFoundError(EmailRenderError):
    """Raised when a required email template file cannot be found."""

    def __init__(self, message: str = "Email template not found.") -> None:
        super().__init__(message)


class EmailRateLimitError(EmailServiceError):
    """Raised when an email send is blocked by rate limiting."""

    def __init__(
        self,
        message: str = "Email rate limit exceeded.",
        *,
        retry_after_seconds: int | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if retry_after_seconds is not None:
            details["retry_after_seconds"] = retry_after_seconds
        super().__init__(
            message,
            status_code=429,
            code="EMAIL_RATE_LIMIT_EXCEEDED",
            details=details,
        )
        self.retry_after_seconds = retry_after_seconds


class EmailSendError(EmailServiceError):
    """Raised when the email provider fails to send an email."""

    def __init__(self, message: str = "Failed to send email through AWS SES.") -> None:
        super().__init__(message, status_code=502, code="EMAIL_SEND_ERROR")
