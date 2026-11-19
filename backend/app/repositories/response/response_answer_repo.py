from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.schema.orm.response.response_answer import ResponseAnswer
from app.schema.types import AnswerLocator, ClientMutationId


def upsert_current(
    db: Session,
    *,
    envelope_id: uuid.UUID,
    answer_locator: AnswerLocator,
    ciphertext: bytes,
    nonce: bytes,
    client_mutation_id: ClientMutationId | None,
) -> ResponseAnswer:
    """Create or overwrite the current encrypted answer for one locator."""
    stmt = (
        insert(ResponseAnswer)
        .values(
            envelope_id=envelope_id,
            answer_locator=answer_locator,
            ciphertext=ciphertext,
            nonce=nonce,
            client_mutation_id=client_mutation_id,
        )
        .on_conflict_do_update(
            index_elements=[ResponseAnswer.answer_locator],
            set_={
                "envelope_id": envelope_id,
                "ciphertext": ciphertext,
                "nonce": nonce,
                "client_mutation_id": client_mutation_id,
                "updated_at": func.now(),
            },
        )
        .returning(ResponseAnswer)
    )
    # Refresh an already-loaded answer when ON CONFLICT returns its replacement.
    return db.scalars(stmt, execution_options={"populate_existing": True}).one()


def get_by_locator(db: Session, answer_locator: AnswerLocator) -> ResponseAnswer | None:
    return db.scalar(select(ResponseAnswer).where(ResponseAnswer.answer_locator == answer_locator))


def get_all_by_envelope(db: Session, envelope_id: uuid.UUID) -> list[ResponseAnswer]:
    return list(db.scalars(select(ResponseAnswer).where(ResponseAnswer.envelope_id == envelope_id)).all())


def get_by_locators(db: Session, answer_locators: Sequence[AnswerLocator]) -> list[ResponseAnswer]:
    """Fetch encrypted answers for a batch of answer locators."""
    if not answer_locators:
        return []
    return list(db.scalars(select(ResponseAnswer).where(ResponseAnswer.answer_locator.in_(answer_locators))).all())
