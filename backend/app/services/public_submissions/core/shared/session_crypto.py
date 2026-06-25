"""Shared session-level crypto mechanics.

Centralises crypto service resolution with caller-provided overrides and the
envelope-lookup + session-DEK unwrap sequence that every action file repeats.

This module is mechanical plumbing — it must not contain domain policy,
transaction management, or action-specific orchestration.
"""

from __future__ import annotations

import struct
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.crypto import (
    CryptoServices,
    SurveyBranchKeyUnavailableError,
    get_crypto_services,
)
from app.domain.errors import EnvelopeNotFoundError
from app.repositories.core import survey_encryption_keys as survey_key_repo
from app.repositories.response import response_envelope_repo

if TYPE_CHECKING:
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
    crypto: CryptoServices | None = None,
    prefetched_branch_key_loader: Callable[[], bytes] | None = None,
) -> bytes:
    crypto = crypto or get_crypto_services()
    survey_branch_key_service = crypto.survey_branch_key_service
    if survey_branch_key_service is None:
        raise SurveyBranchKeyUnavailableError()

    aad = build_session_dek_wrap_aad(
        crypto_version=envelope.crypto_version,
        project_id=session.project_id,
        survey_id=session.survey_id,
        session_id=session.id,
        session_locator=session_locator,
    )

    if prefetched_branch_key_loader is not None:
        branch_key_loader = prefetched_branch_key_loader
    else:
        survey_key = load_survey_encryption_key(db, session=session)

        def branch_key_loader() -> bytes:
            return survey_branch_key_service.get_plaintext_key(survey_key)

    return crypto.dek_service.get_for_session(
        session.id,
        envelope.wrapped_session_dek,
        session.expires_at,
        wrap_aad=aad,
        survey_branch_key_loader=branch_key_loader,
    )


def load_session_envelope_crypto_context(
    db: Session,
    response_db: Session,
    *,
    session: SubmissionSession,
) -> SessionEnvelopeCryptoContext:
    crypto = get_crypto_services()
    session_locator, _ = crypto.locator_service.for_existing_session(
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
        crypto=crypto,
    )

    return SessionEnvelopeCryptoContext(
        session_locator=session_locator,
        envelope=envelope,
        plaintext_dek=plaintext_dek,
    )
