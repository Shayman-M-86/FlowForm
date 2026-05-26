import re

from pydantic import BaseModel, Field, field_validator

from app.schema.api import limits

DISPLAY_NAME_MAX = 100
NICKNAME_MAX = 100
PICTURE_URL_MAX = limits.URL_MAX
USERNAME_MAX = 128

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_.-]+$')


class UpdateProfileRequest(BaseModel):
    """Update display name, nickname, and/or profile picture."""

    display_name: str | None = Field(default=None, max_length=DISPLAY_NAME_MAX)
    nickname: str | None = Field(default=None, max_length=NICKNAME_MAX)
    picture: str | None = Field(default=None, max_length=PICTURE_URL_MAX)

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Display name must not be blank.")
        return value

    @field_validator("nickname")
    @classmethod
    def strip_nickname(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Nickname must not be blank.")
        return value


class ChangeEmailRequest(BaseModel):
    """Request body for changing the account email address."""

    email: str = Field(max_length=limits.EMAIL_MAX)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("Email must not be blank.")
        return value


class ChangeUsernameRequest(BaseModel):
    """Request body for changing the Auth0 username."""

    username: str = Field(min_length=1, max_length=USERNAME_MAX)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username must not be blank.")
        if not _USERNAME_RE.match(value):
            raise ValueError("Username may only contain letters, numbers, underscores, dots, and hyphens.")
        return value
