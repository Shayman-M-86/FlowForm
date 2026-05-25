from datetime import datetime
from typing import Annotated, cast

from pydantic import BaseModel, ConfigDict, Field

from app.domain.permissions import ProjectPermission
from app.schema.api import limits
from app.schema.api.enums import ProjectInvitationStatus, ProjectMemberStatus
from app.schema.orm.core.project import ProjectRole

ProjectMemberStatusOut = Annotated[
    ProjectMemberStatus,
    Field(max_length=limits.PROJECT_MEMBER_STATUS_MAX),
]
ProjectInvitationStatusOut = Annotated[
    ProjectInvitationStatus,
    Field(max_length=limits.PROJECT_INVITATION_STATUS_MAX),
]


class ProjectOut(BaseModel):
    """API response shape for a project."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    created_by_user_id: int | None
    created_at: datetime


class ProjectRoleOut(BaseModel):
    """API response shape for a project role."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    is_system_role: bool
    permissions: list[ProjectPermission] = Field(max_length=limits.PROJECT_ROLE_PERMISSIONS_MAX)
    created_at: datetime

    @classmethod
    def from_orm_with_permissions(cls, role: ProjectRole) -> ProjectRoleOut:
        permissions = [cast(ProjectPermission, p.name) for p in getattr(role, "permissions", [])]
        return cls.model_construct(
            id=role.id,
            project_id=role.project_id,
            name=role.name,
            is_system_role=role.is_system_role,
            permissions=permissions,
            created_at=role.created_at,
        )


class MemberUserOut(BaseModel):
    """Embedded user details on a project member response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str | None


class ProjectMemberOut(BaseModel):
    """API response shape for a project membership."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    project_id: int
    role_id: int | None
    status: ProjectMemberStatusOut
    created_at: datetime
    user: MemberUserOut


class ProjectInvitationOut(BaseModel):
    """API response shape for a project invitation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    project_name: str | None = None
    invited_email: str = Field(max_length=limits.EMAIL_MAX)
    invite_message: str | None = Field(default=None, max_length=limits.INVITE_MESSAGE_MAX)
    invited_by_user_id: int | None
    invited_by_display: str | None = None
    role_id: int | None
    status: ProjectInvitationStatusOut
    expires_at: datetime | None
    accepted_at: datetime | None
    created_at: datetime

    @classmethod
    def from_orm_with_project(cls, invitation: object) -> ProjectInvitationOut:
        """Build response including project name and inviter display from loaded relationships."""
        data = cls.model_validate(invitation)
        project = getattr(invitation, "project", None)
        if project is not None:
            data.project_name = getattr(project, "name", None)
        invited_by = getattr(invitation, "invited_by", None)
        if invited_by is not None:
            data.invited_by_display = getattr(invited_by, "display_name", None) or getattr(invited_by, "email", None)
        return data
