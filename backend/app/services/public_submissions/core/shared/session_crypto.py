"""Shared session-level crypto mechanics.

Centralises crypto service resolution with caller-provided overrides and the
envelope-lookup + session-DEK unwrap sequence that every action file repeats.

This module is mechanical plumbing — it must not contain domain policy,
transaction management, or action-specific orchestration.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.crypto.errors import SurveyBranchKeyUnavailableError
from app.crypto.services import (
    AnswerCryptoService,
    LocatorService,
    SessionDEKService,
    SurveyBranchKeyService,
)
from app.domain.errors import EnvelopeNotFoundError
from app.repositories.core import survey_encryption_keys as survey_key_repo
from app.repositories.response import response_envelope_repo
from app.services.public_submissions.core.shared.crypto_provider import (
    CryptoServices,
    get_crypto_services,
)

if TYPE_CHECKING:
    from app.core.config import EncryptionSettings
    from app.schema.orm.core.submission_session import SubmissionSession
    from app.schema.orm.core.survey_encryption_key import SurveyEncryptionKey
    from app.schema.orm.response.response_envelope import ResponseEnvelope


def build_session_dek_wrap_aad(
    *,
    crypto_version: int,
    project_id: int,
    survey_id: int,
    session_id: UUID,
    session_locator: bytes,
) -> bytes:
    locator_len = len(session_locator)
    return struct.pack(
        f">iqq16sI{locator_len}s",
        crypto_version,
        project_id,
        survey_id,
        session_id.bytes,
        locator_len,
        session_locator,
    )


def resolve_session_crypto_services(
    encryption_settings: EncryptionSettings | None = None,
    *,
    locator_service: LocatorService | None = None,
    dek_service: SessionDEKService | None = None,
    answer_crypto_service: AnswerCryptoService | None = None,
    survey_branch_key_service: SurveyBranchKeyService | None = None,
) -> CryptoServices:
    if locator_service is not None and dek_service is not None and answer_crypto_service is not None:
        crypto = get_crypto_services(encryption_settings)
        return CryptoServices(
            linkage_key_service=crypto.linkage_key_service,
            locator_service=locator_service,
            dek_service=dek_service,
            answer_crypto_service=answer_crypto_service,
            survey_branch_key_service=survey_branch_key_service or crypto.survey_branch_key_service,
        )

    crypto = get_crypto_services(encryption_settings)
    return CryptoServices(
        linkage_key_service=crypto.linkage_key_service,
        locator_service=locator_service or crypto.locator_service,
        dek_service=dek_service or crypto.dek_service,
        answer_crypto_service=answer_crypto_service or crypto.answer_crypto_service,
        survey_branch_key_service=survey_branch_key_service or crypto.survey_branch_key_service,
    )


@dataclass(frozen=True, slots=True)
class SessionEnvelopeCryptoContext:
    """Context for decrypting a session's envelope-protected material."""

    session_locator: bytes
    envelope: ResponseEnvelope
    plaintext_dek: bytes


def load_survey_encryption_key(
    db: Session,
    *,
    session: SubmissionSession,
) -> SurveyEncryptionKey:
    key = survey_key_repo.get_by_project_survey(
        db,
        project_id=session.project_id,
        survey_id=session.survey_id,
    )
    if key is None:
        raise SurveyBranchKeyUnavailableError()
    return key


def load_plaintext_session_dek(
    db: Session,
    *,
    session: SubmissionSession,
    session_locator: bytes,
    envelope: ResponseEnvelope,
    dek_service: SessionDEKService,
    survey_branch_key_service: SurveyBranchKeyService | None,
) -> bytes:
    if survey_branch_key_service is None:
        raise SurveyBranchKeyUnavailableError()

    survey_key = load_survey_encryption_key(db, session=session)
    aad = build_session_dek_wrap_aad(
        crypto_version=envelope.crypto_version,
        project_id=session.project_id,
        survey_id=session.survey_id,
        session_id=session.id,
        session_locator=session_locator,
    )
    return dek_service.get_for_session(
        session.id,
        envelope.wrapped_session_dek,
        session.expires_at,
        wrap_aad=aad,
        survey_branch_key_loader=lambda: survey_branch_key_service.get_plaintext_key(survey_key),
    )


def load_session_envelope_crypto_context(
    db: Session,
    response_db: Session,
    *,
    session: SubmissionSession,
    locator_service: LocatorService,
    dek_service: SessionDEKService,
    survey_branch_key_service: SurveyBranchKeyService | None,
) -> SessionEnvelopeCryptoContext:
    session_locator = locator_service.for_existing_session(
        session.id,
        session.linkage_key_version,
        db,
    )

    envelope = response_envelope_repo.get_by_locator(response_db, session_locator)
    if envelope is None:
        raise EnvelopeNotFoundError()

    plaintext_dek = load_plaintext_session_dek(
        db,
        session=session,
        session_locator=session_locator,
        envelope=envelope,
        dek_service=dek_service,
        survey_branch_key_service=survey_branch_key_service,
    )

    return SessionEnvelopeCryptoContext(
        session_locator=session_locator,
        envelope=envelope,
        plaintext_dek=plaintext_dek,
    )
