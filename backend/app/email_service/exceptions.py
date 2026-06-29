"""Custom exceptions for the email service.

These exceptions keep the rest of the application from depending directly on
Jinja or boto3 error types.
"""


class EmailServiceError(Exception):
    """Base error for all email service failures."""


class EmailConfigError(EmailServiceError):
    """Raised when the email service is missing required configuration."""


class EmailRenderError(EmailServiceError):
    """Raised when an email template cannot be rendered."""


class EmailTemplateNotFoundError(EmailRenderError):
    """Raised when a required email template file cannot be found."""


class EmailSendError(EmailServiceError):
    """Raised when the email provider fails to send an email."""