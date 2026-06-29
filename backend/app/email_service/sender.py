"""AWS SES sender implementation for rendered emails."""

from __future__ import annotations

from email.utils import formataddr
from typing import TYPE_CHECKING, Any

from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import EmailSettings
from app.email_service.exceptions import EmailSendError
from app.email_service.schemas import EmailMessage, EmailRecipient

if TYPE_CHECKING:
    from mypy_boto3_sesv2 import SESV2Client


class SesEmailSender:
    """Send rendered email messages through AWS SES.

    This class does not know about surveys, users, Flask, SQLAlchemy,
    or how AWS clients are created.
    """

    def __init__(
        self,
        *,
        settings: EmailSettings,
        ses_client: SESV2Client,
    ) -> None:
        self.settings = settings
        self.client = ses_client

    def send(self, message: EmailMessage) -> str | None:
        """Send an email message through SES.

        Returns:
            The SES MessageId when available.

        Returns None when email sending is disabled.
        """
        if not self.settings.enabled:
            return None

        payload = self._build_send_email_payload(message)

        try:
            response = self.client.send_email(**payload)
        except (ClientError, BotoCoreError) as exc:
            raise EmailSendError("Failed to send email through AWS SES.") from exc

        message_id = response.get("MessageId")
        return message_id if isinstance(message_id, str) else None

    def _build_send_email_payload(self, message: EmailMessage) -> dict[str, Any]:
        """Build the SES v2 send_email payload."""
        destination: dict[str, list[str]] = {
            "ToAddresses": self._format_recipients(message.to),
        }

        if message.cc:
            destination["CcAddresses"] = self._format_recipients(message.cc)

        if message.bcc:
            destination["BccAddresses"] = self._format_recipients(message.bcc)

        payload: dict[str, Any] = {
            "FromEmailAddress": self._format_from_address(),
            "Destination": destination,
            "Content": {
                "Simple": {
                    "Subject": {
                        "Data": message.subject,
                        "Charset": "UTF-8",
                    },
                    "Body": {
                        "Html": {
                            "Data": message.html_body,
                            "Charset": "UTF-8",
                        },
                        "Text": {
                            "Data": message.text_body,
                            "Charset": "UTF-8",
                        },
                    },
                }
            },
        }

        reply_to = message.reply_to or self.settings.reply_to_address
        if reply_to:
            payload["ReplyToAddresses"] = [reply_to]

        if self.settings.configuration_set_name:
            payload["ConfigurationSetName"] = self.settings.configuration_set_name

        return payload

    def _format_from_address(self) -> str:
        """Format the configured sender address for SES."""
        return self._format_address(
            email=self.settings.from_address,
            name=self.settings.from_name,
        )

    def _format_recipients(self, recipients: list[EmailRecipient]) -> list[str]:
        """Format recipients for SES."""
        return [
            self._format_address(
                email=recipient.email,
                name=recipient.name,
            )
            for recipient in recipients
        ]

    def _format_address(self, *, email: str, name: str | None = None) -> str:
        """Format an email address with an optional display name."""
        if name:
            return formataddr((name, email))

        return email