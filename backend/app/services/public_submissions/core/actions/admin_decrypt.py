"""Admin detail and export decrypt paths.

Authorized callers use these to decrypt session answers for admin detail,
history, and export views. All paths require prior authorization and go
through locator derivation and the decrypt service — never bypassing them.
"""
from __future__ import annotations

import logging
from typing import Any, cast, get_args
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings
from app.crypto import build_aad
from app.crypto.services import AnswerCryptoService, LocatorService, SessionDEKService
from app.crypto.services.answer_crypto_service import DecryptedAnswerPayload
from app.repositories import content_repo as cr
from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
)
from app.schema.api.submission_sessions.answer_payload import (
    SubmissionAnswerValue,
    parse_answer_value,
)
from app.schema.enums import AnswerFamily, QuestionFamily, SubmissionAnswerState
from app.schema.orm.core.submission_session import SubmissionSession
from app.services.public_submissions.core.shared.session_crypto import (
    load_session_envelope_crypto_context,
    resolve_session_crypto_services,
)
from app.services.results import AdminSessionDetailResult, DecryptedAnswerResult

logger = logging.getLogger(__name__)

_QUESTION_FAMILIES: frozenset[str] = frozenset(get_args(QuestionFamily))


def decrypt_session_detail(
    db: Session,
    response_db: Session,
    *,
    session: SubmissionSession,
    encryption_settings: EncryptionSettings,
    locator_service: LocatorService | None = None,
    dek_service: SessionDEKService | None = None,
    answer_crypto_service: AnswerCryptoService | None = None,
) -> AdminSessionDetailResult:
    """Decrypt latest answers for admin detail view.

    Also serves as the decrypt path for export — callers shape the
    AdminSessionDetailResult into the export format (CSV/JSON).

    Authorization contract: callers must verify project and survey
    access before calling. This function accepts a SubmissionSession
    directly and touches response data immediately. Per doc 01 §1,
    the service layer is not responsible for access authorization.
    """
    crypto = resolve_session_crypto_services(
        encryption_settings,
        locator_service=locator_service,
        dek_service=dek_service,
        answer_crypto_service=answer_crypto_service,
    )

    ectx = load_session_envelope_crypto_context(
        db, response_db, session=session,
        locator_service=crypto.locator_service, dek_service=crypto.dek_service,
    )

    answers = response_answer_repo.get_all_by_envelope(response_db, ectx.envelope.id)
    question_meta_map = _build_question_meta_map(db, session.survey_version_id)

    decrypted: list[DecryptedAnswerResult] = []
    for answer in answers:
        latest_rev = response_answer_revision_repo.get_latest(response_db, answer.id)
        if latest_rev is None:
            continue

        parsed = _decrypt_revision(
            ciphertext=latest_rev.ciphertext,
            nonce=latest_rev.nonce,
            dek=ectx.plaintext_dek,
            crypto_version=ectx.envelope.crypto_version,
            envelope_id=answer.envelope_id,
            answer_id=answer.id,
            answer_locator=answer.answer_locator,
            revision_id=latest_rev.id,
            revision_number=latest_rev.revision_number,
            answer_crypto_service=crypto.answer_crypto_service,
        )

        question_key, answer_family = question_meta_map.get(parsed.question_node_id, (None, None))
        decrypted.append(
            DecryptedAnswerResult(
                question_node_id=parsed.question_node_id,
                question_key=question_key,
                answer_family=answer_family,
                answer_state=parsed.answer_state,
                answer_value=_resolve_answer_value(
                    answer_family=answer_family,
                    answer_state=parsed.answer_state,
                    raw_value=parsed.answer_value,
                ),
                revision_number=latest_rev.revision_number,
                revision_id=str(latest_rev.id),
            )
        )

    return AdminSessionDetailResult(
        session_id=str(session.id),
        survey_id=session.survey_id,
        survey_version_id=session.survey_version_id,
        session_status=session.session_status,
        started_at=session.started_at,
        completed_at=session.completed_at,
        answers=decrypted,
    )


def decrypt_session_history(
    db: Session,
    response_db: Session,
    *,
    session: SubmissionSession,
    encryption_settings: EncryptionSettings,
    locator_service: LocatorService | None = None,
    dek_service: SessionDEKService | None = None,
    answer_crypto_service: AnswerCryptoService | None = None,
) -> AdminSessionDetailResult:
    """Decrypt full revision history for authorized history reads."""
    crypto = resolve_session_crypto_services(
        encryption_settings,
        locator_service=locator_service,
        dek_service=dek_service,
        answer_crypto_service=answer_crypto_service,
    )

    ectx = load_session_envelope_crypto_context(
        db, response_db, session=session,
        locator_service=crypto.locator_service, dek_service=crypto.dek_service,
    )

    answers = response_answer_repo.get_all_by_envelope(response_db, ectx.envelope.id)
    question_meta_map = _build_question_meta_map(db, session.survey_version_id)

    decrypted: list[DecryptedAnswerResult] = []
    for answer in answers:
        revisions = response_answer_revision_repo.get_history(response_db, answer.id)
        for rev in revisions:
            parsed = _decrypt_revision(
                ciphertext=rev.ciphertext,
                nonce=rev.nonce,
                dek=ectx.plaintext_dek,
                crypto_version=ectx.envelope.crypto_version,
                envelope_id=answer.envelope_id,
                answer_id=answer.id,
                answer_locator=answer.answer_locator,
                revision_id=rev.id,
                revision_number=rev.revision_number,
                answer_crypto_service=crypto.answer_crypto_service,
            )

            question_key, answer_family = question_meta_map.get(parsed.question_node_id, (None, None))
            decrypted.append(
                DecryptedAnswerResult(
                    question_node_id=parsed.question_node_id,
                    question_key=question_key,
                    answer_family=answer_family,
                    answer_state=parsed.answer_state,
                    answer_value=_resolve_answer_value(
                        answer_family=answer_family,
                        answer_state=parsed.answer_state,
                        raw_value=parsed.answer_value,
                    ),
                    revision_number=rev.revision_number,
                    revision_id=str(rev.id),
                )
            )

    return AdminSessionDetailResult(
        session_id=str(session.id),
        survey_id=session.survey_id,
        survey_version_id=session.survey_version_id,
        session_status=session.session_status,
        started_at=session.started_at,
        completed_at=session.completed_at,
        answers=decrypted,
    )


def _decrypt_revision(
    *,
    ciphertext: bytes,
    nonce: bytes,
    dek: bytes,
    crypto_version: int,
    envelope_id: UUID,
    answer_id: UUID,
    answer_locator: bytes,
    revision_id: UUID,
    revision_number: int,
    answer_crypto_service: AnswerCryptoService,
) -> DecryptedAnswerPayload:
    aad = build_aad(
        crypto_version=crypto_version,
        envelope_id=envelope_id,
        answer_id=answer_id,
        answer_locator=answer_locator,
        revision_id=revision_id,
        revision_number=revision_number,
    )
    return answer_crypto_service.decrypt(dek=dek, ciphertext=ciphertext, nonce=nonce, aad=aad)


def _build_question_meta_map(
    db: Session,
    survey_version_id: int,
) -> dict[str, tuple[str, AnswerFamily | None]]:
    """Map each question node id to its (question_key, answer_family).

    The family is read from the frozen survey definition
    (``question_schema["family"]``) so decrypt can reconstruct it without
    storing it in the encrypted payload. Returns ``None`` for the family when
    the schema lacks a recognizable family value.
    """
    return {
        str(question.id): (
            question.question_key,
            _answer_family_from_schema(question.question_schema),
        )
        for question in cr.list_question_nodes(db, survey_version_id)
    }


def _answer_family_from_schema(question_schema: object) -> AnswerFamily | None:
    """Read the top-level family discriminator from persisted question content."""
    if not isinstance(question_schema, dict):
        return None

    raw_family = question_schema.get("family")
    if raw_family not in _QUESTION_FAMILIES:
        return None

    return cast(AnswerFamily, raw_family)


def _resolve_answer_value(
    *,
    answer_family: AnswerFamily | None,
    answer_state: SubmissionAnswerState,
    raw_value: Any,
) -> SubmissionAnswerValue | dict[str, Any] | None:
    """Validate a decrypted raw value into a canonical model when possible.

    Falls back to the raw value (never raises) when the family is unknown or
    the stored value does not match the canonical shape — e.g. a deleted
    question, a version skew, or legacy ciphertext predating this contract.
    """
    if raw_value is None or answer_state == "cleared" or answer_family is None:
        return raw_value
    if not isinstance(raw_value, dict):
        return raw_value
    try:
        return parse_answer_value(answer_family, raw_value)
    except ValidationError:
        logger.warning(
            "Decrypted answer value did not match canonical %s shape; keeping raw value.",
            answer_family,
        )
        return raw_value
