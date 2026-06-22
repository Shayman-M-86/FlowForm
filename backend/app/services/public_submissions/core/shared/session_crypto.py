"""Shared session-level crypto mechanics.

Centralises KMS context construction, crypto service resolution with
caller-provided overrides, and the envelope-lookup + DEK-unwrap sequence
that every action file repeats.

This module is mechanical plumbing — it must not contain domain policy,
transaction management, or action-specific orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.crypto.services import (
    AnswerCryptoService,
    LocatorService,
    SessionDEKService,
)
from app.domain.errors import EnvelopeNotFoundError
from app.repositories.response import response_envelope_repo
from app.services.public_submissions.core.shared.crypto_provider import (
    CryptoServices,
    build_crypto_services,
)

if TYPE_CHECKING:
    from app.core.config import EncryptionSettings
    from app.schema.orm.core.submission_session import SubmissionSession
    from app.schema.orm.response.response_envelope import ResponseEnvelope

SESSION_KMS_CONTEXT_VERSION = 1


def build_session_kms_context(session_locator: bytes) -> dict[str, str]:
    return {
        "session_locator": session_locator.hex(),
        "kms_context_version": str(SESSION_KMS_CONTEXT_VERSION),
    }


def resolve_session_crypto_services(
    encryption_settings: EncryptionSettings | None = None,
    *,
    locator_service: LocatorService | None = None,
    dek_service: SessionDEKService | None = None,
    answer_crypto_service: AnswerCryptoService | None = None,
) -> CryptoServices:
    if (
        locator_service is not None
        and dek_service is not None
        and answer_crypto_service is not None
    ):
        crypto = build_crypto_services(encryption_settings)
        return CryptoServices(
            linkage_key_service=crypto.linkage_key_service,
            locator_service=locator_service,
            dek_service=dek_service,
            answer_crypto_service=answer_crypto_service,
        )

    crypto = build_crypto_services(encryption_settings)
    return CryptoServices(
        linkage_key_service=crypto.linkage_key_service,
        locator_service=locator_service or crypto.locator_service,
        dek_service=dek_service or crypto.dek_service,
        answer_crypto_service=answer_crypto_service or crypto.answer_crypto_service,
    )


@dataclass(frozen=True, slots=True)
class SessionEnvelopeCryptoContext:
    """Context for decrypting a session's envelope-protected material."""
    session_locator: bytes
    envelope: ResponseEnvelope
    plaintext_dek: bytes


def load_session_envelope_crypto_context(
    db: Session,
    response_db: Session,
    *,
    session: SubmissionSession,
    locator_service: LocatorService,
    dek_service: SessionDEKService,
) -> SessionEnvelopeCryptoContext:
    session_locator = locator_service.for_existing_session(
        str(session.id), session.linkage_key_version, db,
    )

    envelope = response_envelope_repo.get_by_locator(response_db, session_locator)
    if envelope is None:
        raise EnvelopeNotFoundError()

    kms_context = build_session_kms_context(session_locator)
    plaintext_dek = dek_service.get_for_session(
        session.id,
        envelope.wrapped_dek,
        envelope.kms_key_arn,
        session.expires_at,
        encryption_context=kms_context,
    )

    return SessionEnvelopeCryptoContext(
        session_locator=session_locator,
        envelope=envelope,
        plaintext_dek=plaintext_dek,
    )
