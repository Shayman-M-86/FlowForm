from datetime import UTC, datetime

from pydantic import AwareDatetime, BaseModel, field_validator


def _validate_expires_at(value: AwareDatetime | None) -> AwareDatetime | None:
    if value is None:
        return None

    value_utc = value.astimezone(UTC)

    if value_utc <= datetime.now(UTC):
        raise ValueError("expires_at must be a future datetime.")

    return value_utc


def _normalize_assigned_email(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("assigned_email must not be blank.")

    return normalized


class CreatePublicLinkRequest(BaseModel):
    """Request body for creating a survey link."""

    assigned_email: str | None = None
    expires_at: AwareDatetime | None = None

    @field_validator("assigned_email")
    @classmethod
    def validate_assigned_email(cls, value: str | None) -> str | None:
        return _normalize_assigned_email(value)

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: AwareDatetime | None) -> AwareDatetime | None:
        return _validate_expires_at(value)


class UpdatePublicLinkRequest(BaseModel):
    """Request body for partially updating a survey link."""

    is_active: bool | None = None
    assigned_email: str | None = None
    expires_at: AwareDatetime | None = None

    @field_validator("assigned_email")
    @classmethod
    def validate_assigned_email(cls, value: str | None) -> str | None:
        return _normalize_assigned_email(value)

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: AwareDatetime | None) -> AwareDatetime | None:
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
