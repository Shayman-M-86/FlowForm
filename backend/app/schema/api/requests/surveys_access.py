from pydantic import BaseModel, Field

from app.domain.permissions import SurveyPermission
from app.schema.api import limits
from app.schema.api.common.fields import ProjectRoleDescription, ProjectRoleName
from app.schema.api.common.validators import int_id_field, required_int_id_field


class CreateSurveyRoleRequest(BaseModel):
    """Request body for creating a survey role."""

    name: ProjectRoleName
    description: ProjectRoleDescription | None = None
    permissions: set[SurveyPermission] = Field(default_factory=set, max_length=limits.SURVEY_ROLE_PERMISSIONS_MAX)


class UpdateSurveyRoleRequest(BaseModel):
    """Request body for partially updating a survey role."""

    name: ProjectRoleName | None = None
    description: ProjectRoleDescription | None = None
    permissions: set[SurveyPermission] | None = Field(default=None, max_length=limits.SURVEY_ROLE_PERMISSIONS_MAX)


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
