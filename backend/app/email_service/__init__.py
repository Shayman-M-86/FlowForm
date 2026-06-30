"""Standalone email service package."""

from app.email_service.exceptions import EmailRateLimitError
from app.email_service.extension import (
    EmailServiceManager,
    get_email_service,
    get_email_service_manager,
    get_ses_client,
)
from app.email_service.rate_limiter import EmailRateLimiter
from app.email_service.schemas import (
    EmailMessage,
    EmailRecipient,
    ProjectMemberInviteEmail,
    SurveyInviteEmail,
    VerifyEmailEmail,
)
from app.email_service.service import EmailService

__all__ = [
    "EmailMessage",
    "EmailRateLimitError",
    "EmailRateLimiter",
    "EmailRecipient",
    "EmailService",
    "EmailServiceManager",
    "ProjectMemberInviteEmail",
    "SurveyInviteEmail",
    "VerifyEmailEmail",
    "get_email_service",
    "get_email_service_manager",
    "get_ses_client",
]
