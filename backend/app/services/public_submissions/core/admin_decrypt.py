"""Admin detail and export decrypt paths.

Authorized callers use these to decrypt session answers for admin detail,
history, and export views. All paths require prior authorization and go
through locator derivation and the decrypt service — never bypassing them.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings
from app.crypto import (
    build_aad,
    decrypt_answer,
    derive_session_locator,
    get_linkage_secret,
    parse_plaintext_payload,
    unwrap_dek,
)
from app.domain.errors import EnvelopeNotFoundError, SessionInvalidError
from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
    response_envelope_repo,
)
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.core.survey_content import SurveyQuestion
from app.services.results import AdminSessionDetailResult, DecryptedAnswerResult

logger = logging.getLogger(__name__)

_KMS_CONTEXT_VERSION = 1


def decrypt_session_detail(
    db: Session,
    response_db: Session,
    *,
    session: SubmissionSession,
    encryption_settings: EncryptionSettings,
) -> AdminSessionDetailResult:
    """Decrypt latest answers for admin detail view.

    Also serves as the decrypt path for export — callers shape the
    AdminSessionDetailResult into the export format (CSV/JSON).

    Authorization contract: callers must verify project and survey
    access before calling. This function accepts a SubmissionSession
    directly and touches response data immediately. Per doc 01 §1,
    the service layer is not responsible for access authorization.
    """
    envelope, plaintext_dek = _load_envelope_and_dek(
        response_db, session=session, encryption_settings=encryption_settings
    )

    answers = response_answer_repo.get_all_by_envelope(response_db, envelope.id)
    question_key_map = _build_question_key_map(db, session.survey_version_id)

    decrypted: list[DecryptedAnswerResult] = []
    for answer in answers:
        latest_rev = response_answer_revision_repo.get_latest(response_db, answer.id)
        if latest_rev is None:
            continue

        parsed = _decrypt_revision(
            ciphertext=latest_rev.ciphertext,
            nonce=latest_rev.nonce,
            dek=plaintext_dek,
            crypto_version=envelope.crypto_version,
            envelope_id=answer.envelope_id,
            answer_id=answer.id,
            answer_locator=answer.answer_locator,
            revision_id=latest_rev.id,
            revision_number=latest_rev.revision_number,
        )

        decrypted.append(
            DecryptedAnswerResult(
                question_node_id=parsed["question_node_id"],
                question_key=question_key_map.get(parsed["question_node_id"]),
                answer_state=parsed["answer_state"],
                answer_value=parsed["answer_value"],
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
) -> AdminSessionDetailResult:
    """Decrypt full revision history for authorized history reads."""
    envelope, plaintext_dek = _load_envelope_and_dek(
        response_db, session=session, encryption_settings=encryption_settings
    )

    answers = response_answer_repo.get_all_by_envelope(response_db, envelope.id)
    question_key_map = _build_question_key_map(db, session.survey_version_id)

    decrypted: list[DecryptedAnswerResult] = []
    for answer in answers:
        revisions = response_answer_revision_repo.get_history(response_db, answer.id)
        for rev in revisions:
            parsed = _decrypt_revision(
                ciphertext=rev.ciphertext,
                nonce=rev.nonce,
                dek=plaintext_dek,
                crypto_version=envelope.crypto_version,
                envelope_id=answer.envelope_id,
                answer_id=answer.id,
                answer_locator=answer.answer_locator,
                revision_id=rev.id,
                revision_number=rev.revision_number,
            )

            decrypted.append(
                DecryptedAnswerResult(
                    question_node_id=parsed["question_node_id"],
                    question_key=question_key_map.get(parsed["question_node_id"]),
                    answer_state=parsed["answer_state"],
                    answer_value=parsed["answer_value"],
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


def _load_envelope_and_dek(
    response_db: Session,
    *,
    session: SubmissionSession,
    encryption_settings: EncryptionSettings,
) -> tuple[Any, bytes]:
    enc = encryption_settings
    linkage_secret = get_linkage_secret(
        enc.linkage_secret_arn,
        region=enc.aws_region,
        access_key_id=enc.aws_access_key_id,
        secret_access_key=enc.aws_secret_access_key,
    )
    session_locator = derive_session_locator(str(session.id), linkage_secret)

    envelope = response_envelope_repo.get_by_locator(response_db, session_locator)
    if envelope is None:
        raise EnvelopeNotFoundError()

    kms_context = {
        "session_locator": session_locator.hex(),
        "kms_context_version": str(_KMS_CONTEXT_VERSION),
    }
    plaintext_dek = unwrap_dek(
        envelope.wrapped_dek,
        envelope.kms_key_arn,
        kms_context,
        region=enc.aws_region,
        access_key_id=enc.aws_access_key_id,
        secret_access_key=enc.aws_secret_access_key,
    )

    return envelope, plaintext_dek


def _decrypt_revision(
    *,
    ciphertext: bytes,
    nonce: bytes,
    dek: bytes,
    crypto_version: int,
    envelope_id: Any,
    answer_id: Any,
    answer_locator: bytes,
    revision_id: Any,
    revision_number: int,
) -> dict[str, Any]:
    aad = build_aad(
        crypto_version=crypto_version,
        envelope_id=envelope_id,
        answer_id=answer_id,
        answer_locator=answer_locator,
        revision_id=revision_id,
        revision_number=revision_number,
    )
    plaintext_bytes = decrypt_answer(ciphertext, dek, nonce, aad)
    return parse_plaintext_payload(plaintext_bytes)


def _build_question_key_map(db: Session, survey_version_id: int) -> dict[str, str]:
    questions = db.scalars(
        select(SurveyQuestion).where(
            SurveyQuestion.survey_version_id == survey_version_id,
        )
    ).all()
    return {str(q.id): q.question_key for q in questions}
