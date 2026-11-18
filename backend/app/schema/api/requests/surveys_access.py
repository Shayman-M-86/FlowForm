from pydantic import Field

from app.schema.api.common.base import APIRequestModel
from app.schema.api.common.types import SurveyPermissionSet
from app.schema.types import ProjectMembershipId, RoleDescription, RoleName, SurveyRoleId


class CreateSurveyRoleRequest(APIRequestModel):
    """Request body for creating a survey role."""

    name: RoleName
    description: RoleDescription | None = None
    permissions: SurveyPermissionSet = Field(default_factory=set)


class UpdateSurveyRoleRequest(APIRequestModel):
    """Request body for partially updating a survey role."""

    name: RoleName | None = None
    description: RoleDescription | None = None
    permissions: SurveyPermissionSet | None = None


class AssignSurveyMemberRoleRequest(APIRequestModel):
    """Request body for assigning a survey role to a project member for a survey."""

    membership_id: ProjectMembershipId
    role_id: SurveyRoleId


class UpdateSurveyMemberRoleRequest(APIRequestModel):
    """Request body for updating a survey member role assignment."""

    role_id: SurveyRoleId


class RemoveSurveyMemberRoleRequest(APIRequestModel):
    """Request body for removing a survey role from a project member."""

    membership_id: ProjectMembershipId
