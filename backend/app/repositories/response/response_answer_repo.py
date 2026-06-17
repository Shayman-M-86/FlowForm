from __future__ import annotations

import uuid

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schema.orm.response.response_answer import ResponseAnswer

_ANSWER_LOCATOR_CONSTRAINT = "uq_response_answers_envelope_id_answer_locator"


def get_or_create(
    db: Session,
    *,
    envelope_id: uuid.UUID,
    answer_locator: bytes,
    latest_revision_id: uuid.UUID,
) -> tuple[ResponseAnswer, bool]:
    """Return (answer, created). Handles the unique-constraint race on simultaneous first saves."""
    answer = ResponseAnswer(
        envelope_id=envelope_id,
        answer_locator=answer_locator,
        latest_revision_id=latest_revision_id,
    )
    nested = db.begin_nested()
    db.add(answer)
    try:
        nested.commit()
        return answer, True
    except IntegrityError as exc:
        nested.rollback()
        db.expire_all()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "") or ""
        if isinstance(exc.orig, UniqueViolation) and constraint == _ANSWER_LOCATOR_CONSTRAINT:
            existing = db.scalar(
                select(ResponseAnswer).where(
                    ResponseAnswer.envelope_id == envelope_id,
                    ResponseAnswer.answer_locator == answer_locator,
                )
            )
            if existing is not None:
                return existing, False
        raise


def get_by_locator(
    db: Session,
    envelope_id: uuid.UUID,
    answer_locator: bytes,
) -> ResponseAnswer | None:
    return db.scalar(
        select(ResponseAnswer).where(
            ResponseAnswer.envelope_id == envelope_id,
            ResponseAnswer.answer_locator == answer_locator,
        )
    )


def lock_for_update(db: Session, answer_id: uuid.UUID) -> ResponseAnswer | None:
    return db.scalar(
        select(ResponseAnswer)
        .where(ResponseAnswer.id == answer_id)
        .with_for_update()
    )
