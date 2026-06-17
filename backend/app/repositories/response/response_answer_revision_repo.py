from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.response.response_answer import ResponseAnswer
from app.schema.orm.response.response_answer_revision import ResponseAnswerRevision


def create(
    db: Session,
    *,
    answer_id: uuid.UUID,
    envelope_id: uuid.UUID,
    revision_number: int,
    nonce: bytes,
    ciphertext: bytes,
    client_mutation_id: uuid.UUID,
    revision_id: uuid.UUID | None = None,
) -> ResponseAnswerRevision:
    revision = ResponseAnswerRevision(
        answer_id=answer_id,
        envelope_id=envelope_id,
        revision_number=revision_number,
        nonce=nonce,
        ciphertext=ciphertext,
        client_mutation_id=client_mutation_id,
    )
    if revision_id is not None:
        revision.id = revision_id
    db.add(revision)
    flush_with_err_handle(db, contexts=[revision])
    return revision


def get_by_mutation_id(
    db: Session,
    answer_id: uuid.UUID,
    client_mutation_id: uuid.UUID,
) -> ResponseAnswerRevision | None:
    return db.scalar(
        select(ResponseAnswerRevision).where(
            ResponseAnswerRevision.answer_id == answer_id,
            ResponseAnswerRevision.client_mutation_id == client_mutation_id,
        )
    )


def get_latest(db: Session, answer_id: uuid.UUID) -> ResponseAnswerRevision | None:
    answer = db.scalar(
        select(ResponseAnswer).where(ResponseAnswer.id == answer_id)
    )
    if answer is None:
        return None
    return db.scalar(
        select(ResponseAnswerRevision).where(
            ResponseAnswerRevision.id == answer.latest_revision_id,
        )
    )


def get_history(db: Session, answer_id: uuid.UUID) -> list[ResponseAnswerRevision]:
    return list(
        db.scalars(
            select(ResponseAnswerRevision)
            .where(ResponseAnswerRevision.answer_id == answer_id)
            .order_by(ResponseAnswerRevision.revision_number.asc())
        ).all()
    )


def update_latest_pointer(
    db: Session,
    answer_id: uuid.UUID,
    revision_id: uuid.UUID,
) -> None:
    answer = db.scalar(
        select(ResponseAnswer).where(ResponseAnswer.id == answer_id)
    )
    if answer is None:
        return
    answer.latest_revision_id = revision_id
    flush_with_err_handle(db, contexts=[answer])
