from pydantic import BaseModel, Field

from app.domain.permissions import ProjectPermission
from app.schema.api import limits
from app.schema.api.requests.field_types import (
    InviteMessage,
    NormalisedEmail,
    ProjectMemberStatus,
    ProjectName,
    ProjectRoleDescription,
    ProjectRoleName,
    Slug,
)
from app.schema.api.requests.helpers import int_id_field


class CreateProjectRoleRequest(BaseModel):
    """Request body for creating a new project role."""
    name: ProjectRoleName
    description: ProjectRoleDescription | None = None
    permissions: set[ProjectPermission] = Field(
        default_factory=set,
        max_length=limits.PROJECT_ROLE_PERMISSIONS_MAX,
    )


class UpdateProjectRoleRequest(BaseModel):
    """Request body for updating a project role."""
    name: ProjectRoleName | None = None
    description: ProjectRoleDescription | None = None
    permissions: set[ProjectPermission] | None = Field(
        default=None,
        max_length=limits.PROJECT_ROLE_PERMISSIONS_MAX,
    )


class CreateProjectRequest(BaseModel):
    """Request body for creating a new project."""

    name: ProjectName
    slug: Slug


class UpdateMemberRequest(BaseModel):
    """Request body for updating a project membership role and/or status.

    Omit a field to leave it unchanged. Pass role_id: null to clear the role.
    """

    role_id: int | None = int_id_field()
    status: ProjectMemberStatus | None = None


class SendInvitationRequest(BaseModel):
    """Request body for inviting a user to a project by email."""

    email: NormalisedEmail
    role_id: int | None = int_id_field()
    invite_message: InviteMessage | None = None


class UpdateProjectRequest(BaseModel):
    """Request body for partially updating a project."""

    name: ProjectName | None = None
    slug: Slug | None = None
