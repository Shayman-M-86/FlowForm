from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.project_subject import ProjectSubjectIdentity


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
