from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.project_subject import ProjectSubjectIdentity
from app.schema.orm.core.user import User


def get_identity(
    db: Session,
    *,
    project_id: int,
    project_subject_id: UUID,
    identity_id: UUID,
) -> ProjectSubjectIdentity | None:
    return db.scalar(
        select(ProjectSubjectIdentity).where(
            ProjectSubjectIdentity.project_id == project_id,
            ProjectSubjectIdentity.project_subject_id == project_subject_id,
            ProjectSubjectIdentity.id == identity_id,
        )
    )


def get_active_user_identity(
    db: Session,
    *,
    project_id: int,
    user_id: int,
) -> ProjectSubjectIdentity | None:
    return db.scalar(
        select(ProjectSubjectIdentity).where(
            ProjectSubjectIdentity.project_id == project_id,
            ProjectSubjectIdentity.user_id == user_id,
            ProjectSubjectIdentity.identity_type == "authenticated_user",
            ProjectSubjectIdentity.revoked_at.is_(None),
        )
    )


def create_user_identity(
    db: Session,
    *,
    project_id: int,
    project_subject_id: UUID,
    user_id: int,
) -> ProjectSubjectIdentity:
    identity = ProjectSubjectIdentity(
        project_id=project_id,
        project_subject_id=project_subject_id,
        identity_type="authenticated_user",
        user_id=user_id,
        verification_status="verified",
    )
    db.add(identity)
    flush_with_err_handle(db, contexts=[identity])
    return identity


def create_email_identity(
    db: Session,
    *,
    project_id: int,
    project_subject_id: UUID,
    normalized_email: str,
) -> ProjectSubjectIdentity:
    identity = ProjectSubjectIdentity(
        project_id=project_id,
        project_subject_id=project_subject_id,
        identity_type="email",
        normalized_email=normalized_email,
    )
    db.add(identity)
    flush_with_err_handle(db, contexts=[identity])
    return identity


def set_normalized_email(
    db: Session,
    *,
    identity: ProjectSubjectIdentity,
    normalized_email: str,
) -> ProjectSubjectIdentity:
    """Re-point an email identity to a new address. Caller ensures it is email-typed."""
    identity.normalized_email = normalized_email
    flush_with_err_handle(db, contexts=[identity])
    return identity


def link_email_identity_to_user(
    db: Session,
    *,
    identity: ProjectSubjectIdentity,
    user: User,
) -> ProjectSubjectIdentity:
    """Upgrade an email identity in place once the user email has matched it."""
    identity.identity_type = "authenticated_user"
    identity.user_id = user.id
    identity.normalized_email = user.email.strip().lower()
    identity.verification_status = "verified"
    identity.verified_at = datetime.now(UTC)
    flush_with_err_handle(db, contexts=[identity])
    return identity


def delete_identity(db: Session, *, identity: ProjectSubjectIdentity) -> None:
    db.delete(identity)
    flush_with_err_handle(db, contexts=[identity])
