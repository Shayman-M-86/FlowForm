from typing import cast

from pydantic import ConfigDict

from app.schema.api.common.base import APIResponseModel
from app.schema.api.common.types import ProjectPermission, ProjectPermissionSet
from app.schema.enums import ProjectInvitationStatus, ProjectMemberStatus
from app.schema.models.common.types import EmailAddress, Slug, Text, Timestamp
from app.schema.models.identity.types import ProfileName, UserId
from app.schema.models.projects.types import (
    InvitationMessage,
    ProjectId,
    ProjectInvitationId,
    ProjectMembershipId,
    ProjectName,
    ProjectRoleId,
    RoleDescription,
    RoleName,
)
from app.schema.orm.core.project import ProjectRole


class MyProjectPermissionsResponses(APIResponseModel):
    """API response shape for the current user's effective permissions in a project."""

    permissions: ProjectPermissionSet


class ProjectResponses(APIResponseModel):
    """API response shape for a project."""

    model_config = ConfigDict(from_attributes=True)

    id: ProjectId
    name: ProjectName
    slug: Slug
    created_by_user_id: UserId | None
    created_at: Timestamp


class ProjectRoleResponses(APIResponseModel):
    """API response shape for a project role."""

    model_config = ConfigDict(from_attributes=True)

    id: ProjectRoleId
    project_id: ProjectId
    name: RoleName
    description: RoleDescription | None
    is_system_role: bool
    permissions: ProjectPermissionSet
    created_at: Timestamp

    @classmethod
    def from_orm_with_permissions(cls, role: ProjectRole) -> ProjectRoleResponses:
        permissions = {cast(ProjectPermission, p.name) for p in getattr(role, "permissions", [])}
        return cls.model_construct(
            id=role.id,
            project_id=role.project_id,
            name=role.name,
            description=role.description,
            is_system_role=role.is_system_role,
            permissions=permissions,
            created_at=role.created_at,
        )


class MemberUserResponses(APIResponseModel):
    """Embedded user details on a project member response."""

    model_config = ConfigDict(from_attributes=True)

    id: UserId
    email: EmailAddress
    display_name: ProfileName | None


class ProjectMemberResponses(APIResponseModel):
    """API response shape for a project membership."""

    model_config = ConfigDict(from_attributes=True)

    id: ProjectMembershipId
    user_id: UserId
    project_id: ProjectId
    role_id: ProjectRoleId | None
    status: ProjectMemberStatus
    created_at: Timestamp
    user: MemberUserResponses


class ProjectInvitationResponses(APIResponseModel):
    """API response shape for a project invitation."""

    model_config = ConfigDict(from_attributes=True)

    id: ProjectInvitationId
    project_id: ProjectId
    project_name: ProjectName | None = None
    invited_email: EmailAddress
    invite_message: InvitationMessage | None = None
    invited_by_user_id: UserId | None
    invited_by_display: Text | None = None
    role_id: ProjectRoleId | None
    status: ProjectInvitationStatus
    expires_at: Timestamp | None
    accepted_at: Timestamp | None
    created_at: Timestamp

    @classmethod
    def from_orm_with_project(cls, invitation: object) -> ProjectInvitationResponses:
        """Build response including project name and inviter display from loaded relationships."""
        data = cls.model_validate(invitation)
        project = getattr(invitation, "project", None)
        if project is not None:
            data.project_name = getattr(project, "name", None)
        invited_by = getattr(invitation, "invited_by", None)
        if invited_by is not None:
            data.invited_by_display = getattr(invited_by, "display_name", None) or getattr(invited_by, "email", None)
        return data


class PublicInvitationResolveResponse(APIResponseModel):
    """Public-facing response when resolving an invitation token."""

    invited_email: EmailAddress
    project_name: ProjectName
    inviter_name: Text | None = None
    expires_at: Timestamp | None = None
    status: ProjectInvitationStatus
