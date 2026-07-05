from datetime import datetime
from hashlib import sha256
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.error_handling import flush_with_err_handle
from app.schema.enums import ProjectInvitationStatus
from app.schema.orm.core.invitation import ProjectInvitation


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


def _hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def create_invitation(
    db: Session,
    *,
    project_id: int,
    invited_email: str,
    role_id: int | None,
    invited_by_user_id: int | None,
    invite_message: str | None = None,
) -> tuple[ProjectInvitation, str]:
    """Create an invitation and return ``(invitation, raw_token)``.

    The raw token is never persisted — only its SHA-256 hash is stored.
    """
    token = token_urlsafe(32)

    invitation = ProjectInvitation(
        project_id=project_id,
        invited_email=invited_email,
        role_id=role_id,
        invited_by_user_id=invited_by_user_id,
        invite_message=invite_message,
        token_hash=_hash_token(token),
    )
    db.add(invitation)
    flush_with_err_handle(db, contexts=[invitation])
    return invitation, token


def get_by_token(db: Session, token: str) -> ProjectInvitation | None:
    """Look up an invitation by its raw token."""
    hashed = _hash_token(token)
    return db.execute(
        select(ProjectInvitation).where(ProjectInvitation.token_hash == hashed)
    ).scalar_one_or_none()


def update_status(
    db: Session,
    invitation: ProjectInvitation,
    *,
    status: ProjectInvitationStatus,
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
