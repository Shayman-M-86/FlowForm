"""High-level email service.

Application services call this layer.

This file decides which templates to render for each email type, but it does
not know about Flask, SQLAlchemy, routes, ORM models, or AWS client creation.
"""

from __future__ import annotations

from typing import Any

from app.email_service.renderer import EmailRenderer
from app.email_service.schemas import (
    EmailMessage,
    EmailRecipient,
    ProjectMemberInviteEmail,
    SurveyInviteEmail,
    VerifyEmailEmail,
)
from app.email_service.sender import SesEmailSender


class EmailService:
    """Public interface for sending application emails."""

    def __init__(
        self,
        *,
        renderer: EmailRenderer,
        sender: SesEmailSender,
    ) -> None:
        self.renderer = renderer
        self.sender = sender

    def send_survey_invite(self, email: SurveyInviteEmail) -> str | None:
        """Send a survey invitation email."""
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

    def send_verify_email(self, email: VerifyEmailEmail) -> str | None:
        """Send an email verification email."""
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
        email: ProjectMemberInviteEmail,
    ) -> str | None:
        """Send a project member invitation email."""
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

        return self.sender.send(message)