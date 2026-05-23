from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schema.api import limits
from app.schema.api.requests.helpers import validate_slug

ProjectMemberStatus = Annotated[
    Literal["active", "suspended"],
    Field(max_length=limits.PROJECT_MEMBER_STATUS_MAX),
]


ROLE_NAME_MAX = 80
PERMISSION_NAME_MAX = 64


class CreateProjectRoleRequest(BaseModel):
    """Request body for creating a project role."""

    name: str = Field(max_length=ROLE_NAME_MAX)
    permissions: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Role name must not be blank.")
        return value

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, values: list[str]) -> list[str]:
        return [v.strip() for v in values if v.strip()]


class UpdateProjectRoleRequest(BaseModel):
    """Request body for partially updating a project role."""

    name: str | None = Field(default=None, max_length=ROLE_NAME_MAX)
    permissions: list[str] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Role name must not be blank.")
        return value

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        return [v.strip() for v in values if v.strip()]


def _validate_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Name must not be blank.")
    return value


class CreateProjectRequest(BaseModel):
    """Request body for creating a new project."""

    name: str = Field(max_length=limits.PROJECT_NAME_MAX)
    slug: str = Field(max_length=limits.SLUG_MAX)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_name(value)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        return validate_slug(value, field_label="URL-safe name")


class UpdateMemberRequest(BaseModel):
    """Request body for updating a project membership (role and/or status).

    Omit a field to leave it unchanged. Pass role_id: null to clear the role.
    """

    role_id: int | None = Field(default=None, ge=limits.INT_ID_MIN, le=limits.INT_ID_MAX)
    status: ProjectMemberStatus | None = None


class SendInvitationRequest(BaseModel):
    """Request body for inviting a user to a project by email."""

    email: EmailStr = Field(max_length=limits.EMAIL_MAX)
    role_id: int | None = Field(default=None, ge=limits.INT_ID_MIN, le=limits.INT_ID_MAX)
    invite_message: str | None = Field(default=None, max_length=limits.INVITE_MESSAGE_MAX)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip().lower()
        if not value:
            raise ValueError("Email must not be blank.")
        return value

    @field_validator("invite_message")
    @classmethod
    def validate_invite_message(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                return None
        return value


class UpdateProjectRequest(BaseModel):
    """Request body for partially updating a project."""

    name: str | None = Field(default=None, max_length=limits.PROJECT_NAME_MAX)
    slug: str | None = Field(default=None, max_length=limits.SLUG_MAX)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return _validate_name(value) if value is not None else None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        return validate_slug(value, field_label="URL-safe name") if value is not None else None
