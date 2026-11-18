from pydantic import Field

from app.schema.api.common.base import APIRequestModel
from app.schema.api.common.types import ProjectPermissionSet
from app.schema.enums import ProjectMemberStatus
from app.schema.models.common.types import EmailAddress, Slug
from app.schema.models.projects.types import InvitationMessage, ProjectName, ProjectRoleId, RoleDescription, RoleName


class CreateProjectRoleRequest(APIRequestModel):
    """Request body for creating a new project role."""

    name: RoleName
    description: RoleDescription | None = None
    permissions: ProjectPermissionSet = Field(default_factory=set)


class UpdateProjectRoleRequest(APIRequestModel):
    """Request body for updating a project role."""

    name: RoleName | None = None
    description: RoleDescription | None = None
    permissions: ProjectPermissionSet | None = None


class CreateProjectRequest(APIRequestModel):
    """Request body for creating a new project."""

    name: ProjectName
    slug: Slug


class UpdateMemberRequest(APIRequestModel):
    """Request body for updating a project membership role and/or status.

    Omit a field to leave it unchanged. Pass role_id: null to clear the role.
    """

    role_id: ProjectRoleId | None = None
    status: ProjectMemberStatus | None = None


class SendInvitationRequest(APIRequestModel):
    """Request body for inviting a user to a project by email."""

    email: EmailAddress
    role_id: ProjectRoleId | None = None
    invite_message: InvitationMessage | None = None


class UpdateProjectRequest(APIRequestModel):
    """Request body for partially updating a project."""

    name: ProjectName | None = None
    slug: Slug | None = None
