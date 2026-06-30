"""Flask extension wiring for the email service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from flask import Flask, current_app

from app.aws import get_aws_clients
from app.core.config import Settings
from app.email_service.rate_limiter import EmailRateLimiter
from app.email_service.renderer import EmailRenderer
from app.email_service.sender import SesEmailSender
from app.email_service.service import EmailService

if TYPE_CHECKING:
    from mypy_boto3_sesv2 import SESV2Client


EXTENSION_KEY = "email_service"


@dataclass(frozen=True, slots=True)
class EmailServiceResources:
    """Holds the shared email service and AWS SES client."""

    service: EmailService
    ses: SESV2Client


class EmailServiceManager:
    """Owns the shared email service instance for the Flask app."""

    def __init__(self) -> None:
        self._resources: EmailServiceResources | None = None

    def init_app(self, app: Flask) -> None:
        """Initialize the email service and attach it to the Flask app."""
        settings: Settings = app.extensions["settings"]
        email_settings = settings.flowform.email

        ses_client = get_aws_clients(app).sesv2

        renderer = EmailRenderer()
        sender = SesEmailSender(
            settings=email_settings,
            ses_client=ses_client,
        )
        rate_limiter = EmailRateLimiter(settings=email_settings)

        service = EmailService(
            renderer=renderer,
            sender=sender,
            rate_limiter=rate_limiter,
        )

        self._resources = EmailServiceResources(
            service=service,
            ses=ses_client,
        )

        app.extensions[EXTENSION_KEY] = self

    @property
    def resources(self) -> EmailServiceResources:
        """Return email service resources."""
        if self._resources is None:
            raise RuntimeError("Email service is not initialized.")

        return self._resources

    @property
    def service(self) -> EmailService:
        """Return the shared email service."""
        return self.resources.service

    @property
    def ses(self) -> SESV2Client:
        """Return the shared SES client."""
        return self.resources.ses


def get_email_service_manager() -> EmailServiceManager:
    """Return the email service manager from the current Flask app."""
    manager = current_app.extensions.get(EXTENSION_KEY)

    if manager is None:
        raise RuntimeError("Email service is not initialized.")

    return cast(EmailServiceManager, manager)


def get_email_service() -> EmailService:
    """Return the shared email service."""
    return get_email_service_manager().service


def get_ses_client() -> SESV2Client:
    """Return the shared SES client."""
    return get_email_service_manager().ses