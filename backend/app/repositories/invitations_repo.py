from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.invitation import ProjectInvitation
from app.schema.orm.core.project import ProjectRole


def list_pending_by_project(db: Session, project_id: int) -> list[ProjectInvitation]:
    return list(
        db.scalars(
            select(ProjectInvitation)
            .where(
                ProjectInvitation.project_id == project_id,
                ProjectInvitation.status == "pending",
            )
            .order_by(ProjectInvitation.created_at.asc())
        )
    )


def get_by_id(db: Session, invitation_id: int) -> ProjectInvitation | None:
    return db.scalar(
        select(ProjectInvitation).where(ProjectInvitation.id == invitation_id)
    )


def get_pending_by_email(db: Session, *, email: str) -> list[ProjectInvitation]:
    return list(
        db.scalars(
            select(ProjectInvitation)
            .options(
                selectinload(ProjectInvitation.project),
                selectinload(ProjectInvitation.invited_by),
            )
            .where(
                ProjectInvitation.invited_email == email,
                ProjectInvitation.status == "pending",
            )
            .order_by(ProjectInvitation.created_at.asc())
        )
    )


def create_invitation(
    db: Session,
    *,
    project_id: int,
    invited_email: str,
    role_id: int | None,
    invited_by_user_id: int | None,
    invite_message: str | None = None,
) -> ProjectInvitation:
    invitation = ProjectInvitation(
        project_id=project_id,
        invited_email=invited_email,
        role_id=role_id,
        invited_by_user_id=invited_by_user_id,
        invite_message=invite_message,
    )
    db.add(invitation)
    flush_with_err_handle(db, contexts=[invitation])
    return invitation


def update_status(
    db: Session,
    invitation: ProjectInvitation,
    *,
    status: str,
    accepted_by_user_id: int | None = None,
    accepted_at: datetime | None = None,
) -> ProjectInvitation:
    invitation.status = status
    if accepted_by_user_id is not None:
        invitation.accepted_by_user_id = accepted_by_user_id
    if accepted_at is not None:
        invitation.accepted_at = accepted_at
    flush_with_err_handle(db, contexts=[invitation])
    return invitation
