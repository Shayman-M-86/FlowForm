"""High-level email service.

Application services call this layer.

This file decides which templates to render for each email type, but it does
not know about Flask, SQLAlchemy, routes, ORM models, or AWS client creation.
"""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING, Any

from app.core.validation import validate
from app.email_service.renderer import EmailRenderer
from app.email_service.schemas import (
    EmailMessage,
    EmailRecipient,
    ProjectMemberInviteEmail,
    SurveyInviteEmail,
    VerifyEmailEmail,
)
from app.email_service.sender import SesEmailSender

if TYPE_CHECKING:
    from app.email_service.rate_limiter import EmailRateLimiter

logger = getLogger(__name__)


class EmailService:
    """Public interface for sending application emails."""

    def __init__(
        self,
        *,
        renderer: EmailRenderer,
        sender: SesEmailSender,
        rate_limiter: EmailRateLimiter | None = None,
    ) -> None:
        self.renderer = renderer
        self.sender = sender
        self._rate_limiter = rate_limiter

    def send_survey_invite(self, email: SurveyInviteEmail | dict) -> str | None:
        """Send a survey invitation email."""
        email = validate(SurveyInviteEmail, email)
        context = {
            "recipient_name": email.recipient_name,
            "survey_name": email.survey_name,
            "survey_url": str(email.survey_url),
            "expires_at": email.expires_at,
        }

        return self._render_and_send(
            template_base_name="survey_invite",
            subject=f"Survey invitation: {email.survey_name}",
            to_email=email.to_email,
            recipient_name=email.recipient_name,
            context=context,
        )

    def send_verify_email(self, email: VerifyEmailEmail | dict) -> str | None:
        """Send an email verification email."""
        email = validate(VerifyEmailEmail, email)
        context = {
            "recipient_name": email.recipient_name,
            "verify_url": str(email.verify_url),
            "expires_at": email.expires_at,
        }

        return self._render_and_send(
            template_base_name="verify_email",
            subject="Verify your email address",
            to_email=email.to_email,
            recipient_name=email.recipient_name,
            context=context,
        )

    def send_project_member_invite(
        self,
        email: ProjectMemberInviteEmail | dict,
    ) -> str | None:
        """Send a project member invitation email."""
        email = validate(ProjectMemberInviteEmail, email)
        context = {
            "recipient_name": email.recipient_name,
            "inviter_name": email.inviter_name,
            "project_name": email.project_name,
            "invite_url": str(email.invite_url),
            "expires_at": email.expires_at,
        }

        return self._render_and_send(
            template_base_name="project_member_invite",
            subject=f"You've been invited to {email.project_name}",
            to_email=email.to_email,
            recipient_name=email.recipient_name,
            context=context,
        )

    def _render_and_send(
        self,
        *,
        template_base_name: str,
        subject: str,
        to_email: str,
        recipient_name: str | None,
        context: dict[str, Any],
    ) -> str | None:
        """Render HTML/TXT templates and send the final email."""
        log_extra = {"email_type": template_base_name, "to_email": to_email}

        if self._rate_limiter is not None:
            self._rate_limiter.check(
                recipient=to_email, email_type=template_base_name
            )

        html_body, text_body = self.renderer.render_html_and_text(
            template_base_name=template_base_name,
            context=context,
        )

        message = EmailMessage(
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            to=[
                EmailRecipient(
                    email=to_email,
                    name=recipient_name,
                )
            ],
        )

        try:
            message_id = self.sender.send(message)
        except Exception:
            logger.error("email.send_failed", extra=log_extra)
            raise

        if message_id is not None:
            logger.info(
                "email.sent",
                extra={**log_extra, "message_id": message_id},
            )
            if self._rate_limiter is not None:
                self._rate_limiter.record(
                    recipient=to_email, email_type=template_base_name
                )

        return message_id