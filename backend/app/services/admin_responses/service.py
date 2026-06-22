"""Admin response service: decrypt, history, and deletion.

Orchestrates admin response workflows using pre-wired crypto services.
Authorization is the caller's responsibility (per doc 01 §1).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain.errors import EnvelopeNotFoundError, SessionNotFoundError
from app.repositories import content_repo as cr
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
    response_envelope_repo,
)
from app.schema.orm.core.submission_session import SubmissionSession
from app.services.admin_responses.assembler import (
    build_decrypted_answer_result,
    build_question_meta_map,
    decrypt_revision,
)
from app.services.public_submissions.core.shared.crypto_provider import CryptoServices
from app.services.public_submissions.core.shared.session_crypto import (
    load_session_envelope_crypto_context,
)
from app.services.results import (
    AdminSessionDetailResult,
    AdminSessionHistoryResult,
    DecryptedAnswerResult,
    DeletionResult,
)


class AdminResponseService:
    """Admin response viewing, decryption, and deletion."""

    def __init__(self, crypto: CryptoServices) -> None:
        self._crypto = crypto

    def get_session_detail(
        self,
        db: Session,
        response_db: Session,
        *,
        survey_id: int,
        session_id: UUID,
    ) -> AdminSessionDetailResult:
        """Decrypt latest answers for admin detail view."""
        session = _load_session(db, survey_id=survey_id, session_id=session_id)
        ectx = load_session_envelope_crypto_context(
            db, response_db, session=session,
            locator_service=self._crypto.locator_service,
            dek_service=self._crypto.dek_service,
        )

        answers = response_answer_repo.get_all_by_envelope(response_db, ectx.envelope.id)
        question_nodes = cr.list_question_nodes(db, session.survey_version_id)
        question_meta_map = build_question_meta_map(question_nodes)

        decrypted: list[DecryptedAnswerResult] = []
        for answer in answers:
            latest_rev = response_answer_revision_repo.get_latest(response_db, answer.id)
            if latest_rev is None:
                continue

            parsed = decrypt_revision(
                ciphertext=latest_rev.ciphertext,
                nonce=latest_rev.nonce,
                dek=ectx.plaintext_dek,
                crypto_version=ectx.envelope.crypto_version,
                envelope_id=answer.envelope_id,
                answer_id=answer.id,
                answer_locator=answer.answer_locator,
                revision_id=latest_rev.id,
                revision_number=latest_rev.revision_number,
                answer_crypto_service=self._crypto.answer_crypto_service,
            )

            decrypted.append(
                build_decrypted_answer_result(
                    parsed=parsed,
                    question_meta_map=question_meta_map,
                    revision_number=latest_rev.revision_number,
                    revision_id=latest_rev.id,
                )
            )

        return _build_session_result(session, decrypted)

    def get_session_history(
        self,
        db: Session,
        response_db: Session,
        *,
        survey_id: int,
        session_id: UUID,
    ) -> AdminSessionHistoryResult:
        """Decrypt full revision history for authorized history reads."""
        session = _load_session(db, survey_id=survey_id, session_id=session_id)
        ectx = load_session_envelope_crypto_context(
            db, response_db, session=session,
            locator_service=self._crypto.locator_service,
            dek_service=self._crypto.dek_service,
        )

        answers = response_answer_repo.get_all_by_envelope(response_db, ectx.envelope.id)
        question_nodes = cr.list_question_nodes(db, session.survey_version_id)
        question_meta_map = build_question_meta_map(question_nodes)

        decrypted: list[DecryptedAnswerResult] = []
        for answer in answers:
            revisions = response_answer_revision_repo.get_history(response_db, answer.id)
            for rev in revisions:
                parsed = decrypt_revision(
                    ciphertext=rev.ciphertext,
                    nonce=rev.nonce,
                    dek=ectx.plaintext_dek,
                    crypto_version=ectx.envelope.crypto_version,
                    envelope_id=answer.envelope_id,
                    answer_id=answer.id,
                    answer_locator=answer.answer_locator,
                    revision_id=rev.id,
                    revision_number=rev.revision_number,
                    answer_crypto_service=self._crypto.answer_crypto_service,
                )

                decrypted.append(
                    build_decrypted_answer_result(
                        parsed=parsed,
                        question_meta_map=question_meta_map,
                        revision_number=rev.revision_number,
                        revision_id=rev.id,
                    )
                )

        return AdminSessionHistoryResult(session=session, revisions=decrypted)

    def delete_session(
        self,
        db: Session,
        response_db: Session,
        *,
        survey_id: int,
        session_id: UUID,
    ) -> DeletionResult:
        """Delete response data first, then core session.

        Response-first ordering is mandatory per doc 06.
        """
        session = _load_session(db, survey_id=survey_id, session_id=session_id)
        session_locator = self._crypto.locator_service.for_existing_session(
            session.id, session.linkage_key_version, db,
        )

        # Step 1: Delete response DB records (cascade deletes answers + revisions)
        deleted = response_envelope_repo.delete_by_locator(response_db, session_locator)
        if not deleted:
            raise EnvelopeNotFoundError()

        commit_with_err_handle(response_db, contexts=[])

        # Step 2: Delete core session
        ssr.delete_session(db, submission_session=session)
        commit_with_err_handle(db, contexts=[session])

        return DeletionResult(
            session_id=session.id,
            response_deleted=True,
            core_deleted=True,
        )


def _load_session(db: Session, *, survey_id: int, session_id: UUID) -> SubmissionSession:
    session = ssr.get_by_id(db, session_id)
    if session is None or session.survey_id != survey_id:
        raise SessionNotFoundError()
    return session


def _build_session_result(
    session: SubmissionSession,
    decrypted: list[DecryptedAnswerResult],
) -> AdminSessionDetailResult:
    return AdminSessionDetailResult(session=session, answers=decrypted)
