from pydantic import BaseModel, Field, field_validator

from app.domain.permissions import SurveyPermission
from app.schema.api import limits
from app.schema.api.requests.helpers import int_id_field, required_int_id_field


class CreateSurveyRoleRequest(BaseModel):
    """Request body for creating a survey role."""

    name: str = Field(max_length=limits.PROJECT_ROLE_NAME_MAX)
    description: str | None = Field(default=None, max_length=limits.PROJECT_ROLE_DESCRIPTION_MAX)
    permissions: set[SurveyPermission] = Field(
        default_factory=set, max_length=limits.SURVEY_ROLE_PERMISSIONS_MAX
    )

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


class UpdateSurveyRoleRequest(BaseModel):
    """Request body for partially updating a survey role."""

    name: str | None = Field(default=None, max_length=limits.PROJECT_ROLE_NAME_MAX)
    description: str | None = Field(default=None, max_length=limits.PROJECT_ROLE_DESCRIPTION_MAX)
    permissions: set[SurveyPermission] | None = Field(
        default=None, max_length=limits.SURVEY_ROLE_PERMISSIONS_MAX
    )

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


class AssignSurveyMemberRoleRequest(BaseModel):
    """Request body for assigning a survey role to a project member for a survey."""

    membership_id: int = required_int_id_field()
    role_id: int = required_int_id_field()


class UpdateSurveyMemberRoleRequest(BaseModel):
    """Request body for updating a survey member role assignment."""

    role_id: int = required_int_id_field()


class RemoveSurveyMemberRoleRequest(BaseModel):
    """Request body for removing a survey role from a project member."""

    membership_id: int = int_id_field()
