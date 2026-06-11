from __future__ import annotations

import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.project_subject import ProjectSubject

_SUBJECT_CODE_BYTES = 18


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
