from __future__ import annotations

import secrets
from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from sqlalchemy import Row, Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.project_participant import ProjectParticipant
from app.schema.orm.core.project_subject import (
    ProjectSubject,
    ProjectSubjectIdentity,
)
from app.schema.orm.core.submission_session import SubmissionSession

_SUBJECT_CODE_BYTES = 18

CanonicalStatus = Literal["canonical", "alias", "all"]

SubjectListRow = Row[tuple[ProjectSubject, int, UUID | None]]


def generate_subject_code() -> str:
    return f"sub_{secrets.token_urlsafe(_SUBJECT_CODE_BYTES)}"


def get_subject(db: Session, *, project_id: int, subject_id: UUID) -> ProjectSubject | None:
    return db.scalar(
        select(ProjectSubject).where(
            ProjectSubject.project_id == project_id,
            ProjectSubject.id == subject_id,
        )
    )


def create_subject(db: Session, *, project_id: int, subject_code: str | None = None) -> ProjectSubject:
    subject = ProjectSubject(
        project_id=project_id,
        subject_code=subject_code or generate_subject_code(),
    )
    db.add(subject)
    flush_with_err_handle(db, contexts=[subject])
    return subject


def set_subject_code(db: Session, *, subject: ProjectSubject, subject_code: str) -> ProjectSubject:
    subject.subject_code = subject_code
    flush_with_err_handle(db, contexts=[subject])
    return subject


def set_canonical_subject(db: Session, *, subject: ProjectSubject, canonical: ProjectSubject) -> ProjectSubject:
    """Point subject to canonical as a merged/alias row. canonical must be in the same project."""
    subject.canonical_subject_id = canonical.id
    flush_with_err_handle(db, contexts=[subject])
    return subject


def delete_subject(db: Session, *, subject: ProjectSubject) -> None:
    db.delete(subject)
    flush_with_err_handle(db, contexts=[subject])


def _list_subjects_base(
    *,
    project_id: int,
    canonical_status: CanonicalStatus = "canonical",
    is_participant: bool | None = None,
    search: str | None = None,
) -> Select:
    """Build the shared WHERE clause for list_subjects and its count query."""
    active_identity_count = (
        select(func.count())
        .where(
            ProjectSubjectIdentity.project_id == ProjectSubject.project_id,
            ProjectSubjectIdentity.project_subject_id == ProjectSubject.id,
            ProjectSubjectIdentity.revoked_at.is_(None),
        )
        .correlate(ProjectSubject)
        .scalar_subquery()
        .label("active_identity_count")
    )

    participant_id = (
        select(ProjectParticipant.id)
        .where(
            ProjectParticipant.project_id == ProjectSubject.project_id,
            ProjectParticipant.project_subject_id == ProjectSubject.id,
        )
        .correlate(ProjectSubject)
        .scalar_subquery()
        .label("participant_id")
    )

    stmt = select(ProjectSubject, active_identity_count, participant_id).where(ProjectSubject.project_id == project_id)

    if canonical_status == "canonical":
        stmt = stmt.where(ProjectSubject.canonical_subject_id.is_(None))
    elif canonical_status == "alias":
        stmt = stmt.where(ProjectSubject.canonical_subject_id.is_not(None))

    if is_participant is True:
        stmt = stmt.where(
            select(ProjectParticipant.id)
            .where(
                ProjectParticipant.project_id == ProjectSubject.project_id,
                ProjectParticipant.project_subject_id == ProjectSubject.id,
            )
            .correlate(ProjectSubject)
            .exists()
        )
    elif is_participant is False:
        stmt = stmt.where(
            ~select(ProjectParticipant.id)
            .where(
                ProjectParticipant.project_id == ProjectSubject.project_id,
                ProjectParticipant.project_subject_id == ProjectSubject.id,
            )
            .correlate(ProjectSubject)
            .exists()
        )

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                ProjectSubject.subject_code.ilike(pattern),
                select(ProjectSubjectIdentity.id)
                .where(
                    ProjectSubjectIdentity.project_id == ProjectSubject.project_id,
                    ProjectSubjectIdentity.project_subject_id == ProjectSubject.id,
                    ProjectSubjectIdentity.revoked_at.is_(None),
                    ProjectSubjectIdentity.normalized_email.ilike(pattern),
                )
                .correlate(ProjectSubject)
                .exists(),
            )
        )

    return stmt


def list_subjects(
    db: Session,
    *,
    project_id: int,
    canonical_status: CanonicalStatus = "canonical",
    is_participant: bool | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[Sequence[SubjectListRow], int]:
    """Return paginated subjects with active_identity_count and participant_id."""
    base = _list_subjects_base(
        project_id=project_id,
        canonical_status=canonical_status,
        is_participant=is_participant,
        search=search,
    )

    count_stmt = select(func.count()).select_from(base.with_only_columns(ProjectSubject.id).subquery())
    total = db.scalar(count_stmt) or 0

    rows: Sequence[SubjectListRow] = db.execute(
        base.order_by(ProjectSubject.created_at.desc()).offset(offset).limit(limit)
    ).all()

    return rows, total


def get_subject_with_participant(
    db: Session, *, project_id: int, subject_id: UUID
) -> tuple[ProjectSubject, UUID | None] | None:
    """Fetch a subject with its participant_id (if enrolled).

    Active identities are eagerly loaded via the ORM relationship.
    """
    participant_id = (
        select(ProjectParticipant.id)
        .where(
            ProjectParticipant.project_id == ProjectSubject.project_id,
            ProjectParticipant.project_subject_id == ProjectSubject.id,
        )
        .correlate(ProjectSubject)
        .scalar_subquery()
        .label("participant_id")
    )

    row = (
        db.execute(
            select(ProjectSubject, participant_id)
            .options(joinedload(ProjectSubject.identities))
            .where(
                ProjectSubject.project_id == project_id,
                ProjectSubject.id == subject_id,
            )
        )
        .unique()
        .first()
    )

    if row is None:
        return None

    return row[0], row[1]


def list_subjects_by_survey(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
    offset: int = 0,
    limit: int = 50,
) -> tuple[Sequence[ProjectSubject], int]:
    """Return paginated subjects with at least one session in this survey."""
    has_session = (
        select(SubmissionSession.id)
        .where(
            SubmissionSession.project_subject_id == ProjectSubject.id,
            SubmissionSession.survey_id == survey_id,
        )
        .correlate(ProjectSubject)
        .exists()
    )
    base = select(ProjectSubject).where(ProjectSubject.project_id == project_id, has_session)

    total = db.scalar(select(func.count()).select_from(base.with_only_columns(ProjectSubject.id).subquery())) or 0

    rows = db.scalars(base.order_by(ProjectSubject.created_at.desc()).offset(offset).limit(limit)).all()

    return rows, total


def get_subject_in_survey(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
    subject_id: UUID,
) -> ProjectSubject | None:
    """Fetch a subject only if it has at least one session in this survey."""
    has_session = (
        select(SubmissionSession.id)
        .where(
            SubmissionSession.project_subject_id == ProjectSubject.id,
            SubmissionSession.survey_id == survey_id,
        )
        .correlate(ProjectSubject)
        .exists()
    )
    return db.scalar(
        select(ProjectSubject).where(
            ProjectSubject.project_id == project_id,
            ProjectSubject.id == subject_id,
            has_session,
        )
    )
