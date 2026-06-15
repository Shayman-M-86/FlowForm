from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.project_participant import ProjectParticipant


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


def list_participants(db: Session, *, project_id: int) -> list[ProjectParticipant]:
    return list(
        db.scalars(
            select(ProjectParticipant).where(ProjectParticipant.project_id == project_id)
        )
    )


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
