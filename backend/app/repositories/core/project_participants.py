from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.project_participant import ProjectParticipant
from app.schema.orm.core.project_subject import ProjectSubject, ProjectSubjectIdentity


def get_participant(db: Session, *, project_id: int, participant_id: UUID) -> ProjectParticipant | None:
    return db.scalar(
        select(ProjectParticipant).where(
            ProjectParticipant.project_id == project_id,
            ProjectParticipant.id == participant_id,
        )
    )


def get_participant_by_subject(
    db: Session,
    *,
    project_id: int,
    project_subject_id: UUID,
) -> ProjectParticipant | None:
    return db.scalar(
        select(ProjectParticipant).where(
            ProjectParticipant.project_id == project_id,
            ProjectParticipant.project_subject_id == project_subject_id,
        )
    )


def list_participants(
    db: Session,
    *,
    project_id: int,
    search: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[ProjectParticipant], int]:
    stmt = (
        select(ProjectParticipant)
        .where(ProjectParticipant.project_id == project_id)
        .options(joinedload(ProjectParticipant.subject), joinedload(ProjectParticipant.identity))
    )

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                ProjectSubject.subject_code.ilike(pattern),
                ProjectSubjectIdentity.normalized_email.ilike(pattern),
            )
        ).join(
            ProjectSubject,
            (ProjectParticipant.project_id == ProjectSubject.project_id)
            & (ProjectParticipant.project_subject_id == ProjectSubject.id),
        ).join(
            ProjectSubjectIdentity,
            (ProjectParticipant.project_id == ProjectSubjectIdentity.project_id)
            & (ProjectParticipant.project_subject_id == ProjectSubjectIdentity.project_subject_id)
            & (ProjectParticipant.identity_id == ProjectSubjectIdentity.id),
        )

    count_stmt = select(func.count()).select_from(
        stmt.with_only_columns(ProjectParticipant.id).subquery()
    )
    total = db.scalar(count_stmt) or 0

    rows = list(
        db.scalars(
            stmt.order_by(ProjectParticipant.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).unique()
    )

    return rows, total


def create_participant(
    db: Session,
    *,
    project_id: int,
    project_subject_id: UUID,
    identity_id: UUID,
) -> ProjectParticipant:
    """Insert a participant for a subject under a specific identity.

    The subject and identity must already exist; the database enforces that the
    identity belongs to the subject within the same project. A second participant
    for the same subject violates ``uq_project_participants_project_subject`` and
    surfaces as a conflict through the integrity-rules layer.
    """
    participant = ProjectParticipant(
        project_id=project_id,
        project_subject_id=project_subject_id,
        identity_id=identity_id,
    )
    db.add(participant)
    flush_with_err_handle(db, contexts=[participant])
    return participant


def delete_participant(db: Session, *, participant: ProjectParticipant) -> None:
    """Delete a participant. Blocked by RESTRICT if a survey_link still assigns it."""
    db.delete(participant)
    flush_with_err_handle(db, contexts=[participant])
