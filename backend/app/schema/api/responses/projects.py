from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectOut(BaseModel):
    """API response shape for a project."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    created_by_user_id: int | None
    created_at: datetime


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
    status: str
    created_at: datetime
    user: MemberUserOut


class ProjectInvitationOut(BaseModel):
    """API response shape for a project invitation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    project_name: str | None = None
    invited_email: str
    invite_message: str | None = None
    invited_by_user_id: int | None
    invited_by_display: str | None = None
    role_id: int | None
    status: str
    expires_at: datetime | None
    accepted_at: datetime | None
    created_at: datetime

    @classmethod
    def from_orm_with_project(cls, invitation: object) -> "ProjectInvitationOut":
        """Build response including project name and inviter display from loaded relationships."""
        data = cls.model_validate(invitation)
        project = getattr(invitation, "project", None)
        if project is not None:
            data.project_name = getattr(project, "name", None)
        invited_by = getattr(invitation, "invited_by", None)
        if invited_by is not None:
            data.invited_by_display = getattr(invited_by, "display_name", None) or getattr(invited_by, "email", None)
        return data
