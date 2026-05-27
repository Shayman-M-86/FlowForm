from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.domain.permissions import ProjectPermission
from app.schema.api import limits
from app.schema.api.enums import ProjectMemberStatus as ProjectMemberStatusValue
from app.schema.api.requests.helpers import int_id_field, validate_slug

ProjectMemberStatus = Annotated[
    ProjectMemberStatusValue,
    Field(max_length=limits.PROJECT_MEMBER_STATUS_MAX),
]


class CreateProjectRoleRequest(BaseModel):
    """Request body for creating a project role."""

    name: str = Field(max_length=limits.PROJECT_ROLE_NAME_MAX)
    description: str | None = Field(default=None, max_length=limits.PROJECT_ROLE_DESCRIPTION_MAX)
    permissions: set[ProjectPermission] = Field(default_factory=set, max_length=limits.PROJECT_ROLE_PERMISSIONS_MAX)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Role name must not be blank.")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Role description must not be blank.")
        return value


class UpdateProjectRoleRequest(BaseModel):
    """Request body for partially updating a project role."""

    name: str | None = Field(default=None, max_length=limits.PROJECT_ROLE_NAME_MAX)
    description: str | None = Field(default=None, max_length=limits.PROJECT_ROLE_DESCRIPTION_MAX)
    permissions: set[ProjectPermission] | None = Field(default=None, max_length=limits.PROJECT_ROLE_PERMISSIONS_MAX)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Role name must not be blank.")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Role description must not be blank.")
        return value


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

    role_id: int | None = int_id_field()
    status: ProjectMemberStatus | None = None


class SendInvitationRequest(BaseModel):
    """Request body for inviting a user to a project by email."""

    email: EmailStr = Field(max_length=limits.EMAIL_MAX)
    role_id: int | None = int_id_field()
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
        if value:
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
