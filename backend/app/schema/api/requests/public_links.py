from datetime import UTC, datetime

from pydantic import BaseModel, field_validator


def _validate_expires_at(value: datetime | None) -> datetime | None:
    if value is not None and value <= datetime.now(tz=UTC):
        raise ValueError("expires_at must be a future datetime.")
    return value


class CreatePublicLinkRequest(BaseModel):
    """Request body for creating a public share link for a survey."""

    allow_response: bool = True
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: datetime | None) -> datetime | None:
        return _validate_expires_at(value)


class UpdatePublicLinkRequest(BaseModel):
    """Request body for partially updating a public share link."""

    is_active: bool | None = None
    allow_response: bool | None = None
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: datetime | None) -> datetime | None:
        return _validate_expires_at(value)


class ResolveTokenRequest(BaseModel):
    """Request body for resolving a public link token to its associated survey and project."""

    token: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("token must not be blank.")
        return value
