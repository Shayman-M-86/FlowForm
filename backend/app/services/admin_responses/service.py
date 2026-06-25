"""Admin response service: decrypt, history, and deletion.

Authorization is the caller's responsibility (per doc 01 §1).
"""

from __future__ import annotations

import logging
from typing import Any, cast, get_args
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.crypto.answers import decrypt_answer_revision
from app.crypto.locators import resolve_existing_session_locator
from app.crypto.models import (
    AnswerLocator,
    RevisionContext,
)
from app.crypto.session_key import load_session_envelope_crypto_context
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import EnvelopeNotFoundError, SessionNotFoundError
from app.repositories import content_repo as cr
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
    response_envelope_repo,
)
from app.schema.api.submission_sessions.answer_payload import (
    SubmissionAnswerValue,
    parse_answer_value,
)
from app.schema.enums import AnswerFamily, QuestionFamily, SubmissionAnswerState
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.core.survey_content import SurveyQuestion
from app.services.results import (
    AdminSessionDetailResult,
    AdminSessionHistoryResult,
    DecryptedAnswerResult,
    DeletionResult,
)

logger = logging.getLogger(__name__)

_QUESTION_FAMILIES: frozenset[str] = frozenset(get_args(QuestionFamily))
QuestionMetaMap = dict[UUID, tuple[str, AnswerFamily | None]]


class AdminResponseService:
    """Admin response viewing, decryption, and deletion."""

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
            db,
            response_db,
            session=session,
        )

        answers = response_answer_repo.get_all_by_envelope(response_db, ectx.envelope.id)
        question_nodes = cr.list_question_nodes(db, session.survey_version_id)
        question_meta_map = _build_question_meta_map(question_nodes)

        decrypted: list[DecryptedAnswerResult] = []
        for answer in answers:
            latest_rev = response_answer_revision_repo.get_latest(response_db, answer.id)
            if latest_rev is None:
                continue

            decrypted.append(_decrypt_to_result(ectx, answer, latest_rev, question_meta_map))

        return AdminSessionDetailResult(session=session, answers=decrypted)

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
            db,
            response_db,
            session=session,
        )

        answers = response_answer_repo.get_all_by_envelope(response_db, ectx.envelope.id)
        question_nodes = cr.list_question_nodes(db, session.survey_version_id)
        question_meta_map = _build_question_meta_map(question_nodes)

        decrypted: list[DecryptedAnswerResult] = []
        for answer in answers:
            revisions = response_answer_revision_repo.get_history(response_db, answer.id)
            for rev in revisions:
                decrypted.append(_decrypt_to_result(ectx, answer, rev, question_meta_map))

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
        session_locator, _ = resolve_existing_session_locator(
            db,
            session.id,
            session.linkage_key_version,
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


def _decrypt_to_result(ectx, answer, rev, question_meta_map: QuestionMetaMap) -> DecryptedAnswerResult:
    parsed = decrypt_answer_revision(**_decrypt_revision_args(ectx, answer, rev))
    question_key, answer_family = question_meta_map.get(
        parsed.question_node_id,
        (None, None),
    )
    return DecryptedAnswerResult(
        question_node_id=parsed.question_node_id,
        question_key=question_key,
        answer_family=answer_family,
        answer_state=parsed.answer_state,
        answer_value=_resolve_answer_value(
            answer_family=answer_family,
            answer_state=parsed.answer_state,
            raw_value=parsed.answer_value,
        ),
        revision_id=rev.id,
        revision_number=rev.revision_number,
    )


def _decrypt_revision_args(ectx, answer, rev) -> dict:
    return {
        "ciphertext": rev.ciphertext,
        "nonce": rev.nonce,
        "context": RevisionContext(
            dek=ectx.plaintext_key,
            crypto_version=ectx.envelope.crypto_version,
            envelope_id=answer.envelope_id,
            answer_id=answer.id,
            answer_locator=AnswerLocator(answer.answer_locator),
            revision_id=rev.id,
            revision_number=rev.revision_number,
        ),
    }


def _load_session(db: Session, *, survey_id: int, session_id: UUID) -> SubmissionSession:
    session = ssr.get_by_id(db, session_id)
    if session is None or session.survey_id != survey_id:
        raise SessionNotFoundError()
    return session


def _build_question_meta_map(
    question_nodes: list[SurveyQuestion],
) -> QuestionMetaMap:
    """Map each question node id to its question key and answer family."""
    return {q.id: (q.question_key, _answer_family_from_schema(q.question_schema)) for q in question_nodes}


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
    """Validate decrypted raw values into canonical answer models when possible."""
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
