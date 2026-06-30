from __future__ import annotations

import uuid

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schema.orm.core.submission_answer_slot import SubmissionAnswerSlot

_SLOT_CONSTRAINT = "uq_submission_answer_slots_session_question"


def get_or_create(
    db: Session,
    *,
    submission_session_id: uuid.UUID,
    survey_version_id: int,
    question_node_id: uuid.UUID,
    question_key: str | None,
) -> SubmissionAnswerSlot:
    """Return the stable answer slot for a session/question, creating it once."""
    slot = SubmissionAnswerSlot(
        submission_session_id=submission_session_id,
        survey_version_id=survey_version_id,
        question_node_id=question_node_id,
        question_key=question_key,
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
                    SubmissionAnswerSlot.question_node_id == question_node_id,
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
