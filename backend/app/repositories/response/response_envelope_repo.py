from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.response.response_envelope import ResponseEnvelope


def create(
    db: Session,
    *,
    session_locator: bytes,
    linkage_key_version: int,
    wrapped_session_dek: bytes,
    crypto_version: int,
) -> ResponseEnvelope:
    envelope = ResponseEnvelope(
        session_locator=session_locator,
        linkage_key_version=linkage_key_version,
        wrapped_session_dek=wrapped_session_dek,
        crypto_version=crypto_version,
    )
    db.add(envelope)
    flush_with_err_handle(db, contexts=[envelope])
    return envelope


def get_by_locator(db: Session, session_locator: bytes) -> ResponseEnvelope | None:
    return db.scalar(
        select(ResponseEnvelope).where(ResponseEnvelope.session_locator == session_locator)
    )


def delete_by_locator(db: Session, session_locator: bytes) -> bool:
    """Delete an envelope by session locator. Returns True if a row was deleted."""
    envelope = get_by_locator(db, session_locator)
    if envelope is None:
        return False
    db.delete(envelope)
    db.flush()
    return True
