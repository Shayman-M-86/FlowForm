"""Schema objects for the email service.

These models deliberately use plain values only.
Do not pass Flask objects, SQLAlchemy sessions, or ORM models into this layer.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class EmailRecipient(BaseModel):
    """A single email recipient."""

    model_config = ConfigDict(frozen=True)

    email: EmailStr
    name: str | None = None


class EmailMessage(BaseModel):
    """A fully rendered email ready to send."""

    model_config = ConfigDict(frozen=True)

    subject: str = Field(min_length=1)
    html_body: str = Field(min_length=1)
    text_body: str = Field(min_length=1)

    to: list[EmailRecipient] = Field(min_length=1)
    cc: list[EmailRecipient] = Field(default_factory=list)
    bcc: list[EmailRecipient] = Field(default_factory=list)

    reply_to: EmailStr | None = None


class SurveyInviteEmail(BaseModel):
    """Input data for a survey invitation email."""

    model_config = ConfigDict(frozen=True)

    to_email: EmailStr
    recipient_name: str | None = None

    survey_name: str = Field(min_length=1)
    survey_url: str | HttpUrl

    expires_at: datetime | None = None


class PasswordResetEmail(BaseModel):
    """Input data for a password reset email."""

    model_config = ConfigDict(frozen=True)

    to_email: EmailStr
    recipient_name: str | None = None

    reset_url: HttpUrl
    expires_at: datetime | None = None


class VerifyEmailEmail(BaseModel):
    """Input data for an email verification email."""

    model_config = ConfigDict(frozen=True)

    to_email: EmailStr
    recipient_name: str | None = None

    verify_url: HttpUrl
    expires_at: datetime | None = None


class ProjectMemberInviteEmail(BaseModel):
    """Input data for a project member invitation email."""

    model_config = ConfigDict(frozen=True)

    to_email: EmailStr
    recipient_name: str | None = None

    inviter_name: str | None = None
    project_name: str = Field(min_length=1)
    invite_url: HttpUrl
    expires_at: datetime | None = None
