from __future__ import annotations

import uuid

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schema.orm.core.submission_answer_slot import SubmissionAnswerSlot

_SLOT_CONSTRAINT = "uq_submission_answer_slots_session_field"


def get_or_create(
    db: Session,
    *,
    submission_session_id: uuid.UUID,
    survey_version_id: int,
    field_id: str,
) -> SubmissionAnswerSlot:
    """Return the stable answer slot for a session/field, creating it once."""
    slot = SubmissionAnswerSlot(
        submission_session_id=submission_session_id,
        survey_version_id=survey_version_id,
        field_id=field_id,
    )
    nested = db.begin_nested()
    db.add(slot)
    try:
        nested.commit()
        return slot
    except IntegrityError as exc:
        nested.rollback()
        db.expire_all()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "") or ""
        if isinstance(exc.orig, UniqueViolation) and constraint == _SLOT_CONSTRAINT:
            existing = db.scalar(
                select(SubmissionAnswerSlot).where(
                    SubmissionAnswerSlot.submission_session_id == submission_session_id,
                    SubmissionAnswerSlot.field_id == field_id,
                )
            )
            if existing is not None:
                return existing
        raise


def list_by_session(db: Session, *, submission_session_id: uuid.UUID) -> list[SubmissionAnswerSlot]:
    """Return all answer slots for one session."""
    return list(
        db.scalars(
            select(SubmissionAnswerSlot).where(SubmissionAnswerSlot.submission_session_id == submission_session_id)
        ).all()
    )
