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
    wrapped_dek: bytes,
    kms_key_arn: str,
    kms_context_version: int,
    crypto_version: int,
) -> ResponseEnvelope:
    envelope = ResponseEnvelope(
        session_locator=session_locator,
        linkage_key_version=linkage_key_version,
        wrapped_dek=wrapped_dek,
        kms_key_arn=kms_key_arn,
        kms_context_version=kms_context_version,
        crypto_version=crypto_version,
    )
    db.add(envelope)
    flush_with_err_handle(db, contexts=[envelope])
    return envelope


def get_by_locator(db: Session, session_locator: bytes) -> ResponseEnvelope | None:
    return db.scalar(
        select(ResponseEnvelope).where(ResponseEnvelope.session_locator == session_locator)
    )
