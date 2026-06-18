"""Answer save orchestration following the exact 12-step sequence from doc 03.

Also provides the question-viewed event helper.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto import (
    build_aad,
    build_plaintext_payload,
    derive_answer_locator,
    encrypt_answer,
    generate_nonce,
    get_linkage_secret,
    unwrap_dek,
)
from app.crypto.dek_cache import DekCache
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import AnswerSaveError, QuestionNotInVersionError, SessionInvalidError
from app.repositories.core import submission_events as event_repo
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_answer_repo, response_answer_revision_repo
from app.schema.orm.core.survey_content import SurveyQuestion
from app.services.public_submissions.core.session_loader import SessionContext

logger = logging.getLogger(__name__)

_PAYLOAD_VERSION = 1
_KMS_CONTEXT_VERSION = 1


class AnswerSaveService:
    """Service for orchestrating the 12-step answer save sequence.

    Handles encryption, validation, and persistence of survey answers with
    proper session management and duplicate detection.
    """

    def __init__(
        self,
        *,
        dek_cache: DekCache | None = None,
    ) -> None:
        self._dek_cache = dek_cache

    def save_answer(
        self,
        db: Session,
        response_db: Session,
        *,
        ctx: SessionContext,
        question_node_id: str,
        answer_state: str,
        answer_value: Any | None,
        client_mutation_id: uuid.UUID,
    ) -> uuid.UUID:
        """Execute the 12-step answer save sequence. Returns the revision ID."""
        # Step 1: Validate and lock the current session
        locked_session = ssr.lock_for_update(db, ctx.session.id)
        if locked_session is None:
            raise AnswerSaveError("Session disappeared during answer save.")
        if locked_session.session_status != "in_progress":
            raise SessionInvalidError(f"Session is {locked_session.session_status}.")

        # Step 2: Check mutation ID — before any row lock on the logical answer
        answer_locator = self._derive_answer_locator(ctx, question_node_id)
        existing_answer = response_answer_repo.get_by_locator(response_db, ctx.envelope.id, answer_locator)
        if existing_answer is not None:
            dup_revision = response_answer_revision_repo.get_by_mutation_id(
                response_db, existing_answer.id, client_mutation_id
            )
            if dup_revision is not None:
                return dup_revision.id

        # Step 3: Validate the answer against the frozen survey version
        question = self._validate_question_in_version(db, ctx, question_node_id)

        # Step 3b: Validate answer shape against question family
        if answer_state != "cleared" and answer_value is not None:
            from app.domain.survey_answer_validation import validate_answer_shape

            family = (question.question_schema or {}).get("family")
            validate_answer_shape(family, answer_value)

        # Step 4: Derive session locator and answer locator (locator already derived)
        # Step 5: Load the response envelope (already in ctx)

        # Step 6: Load plaintext DEK from cache; on miss, unwrap with KMS
        plaintext_dek = self._get_or_unwrap_dek(ctx)

        # Step 7: Encrypt the answer payload. ``answer_value`` is the JSON form of
        # a canonical SubmissionAnswerValue; the family is not stored (it is
        # reconstructed from the survey definition at decrypt time).
        plaintext = build_plaintext_payload(
            payload_version=_PAYLOAD_VERSION,
            question_node_id=question_node_id,
            answer_state=answer_state,
            answer_value=answer_value,
        )

        # Steps 8-9: Insert revision and update latest pointer
        if existing_answer is not None:
            # Changed answer: lock the logical answer row
            locked_answer = response_answer_repo.lock_for_update(response_db, existing_answer.id)
            if locked_answer is None:
                raise AnswerSaveError("Logical answer row disappeared.")

            latest_rev = response_answer_revision_repo.get_latest(response_db, locked_answer.id)
            next_revision_number = (latest_rev.revision_number + 1) if latest_rev else 1
        else:
            next_revision_number = 1

        # We need the revision ID for AAD before creating. Pre-generate it.
        revision_id = uuid.uuid4()

        if existing_answer is None:
            # First save: create logical answer row with the revision we're about to insert
            answer_row, created = response_answer_repo.get_or_create(
                response_db,
                envelope_id=ctx.envelope.id,
                answer_locator=answer_locator,
                latest_revision_id=revision_id,
            )
            if not created:
                # Lost the race — another writer created the answer row first.
                # Check for mutation ID dedup again, then proceed as changed answer.
                dup_revision = response_answer_revision_repo.get_by_mutation_id(
                    response_db, answer_row.id, client_mutation_id
                )
                if dup_revision is not None:
                    return dup_revision.id
                locked_answer = response_answer_repo.lock_for_update(response_db, answer_row.id)
                if locked_answer is None:
                    raise AnswerSaveError("Logical answer row disappeared after race.")
                latest_rev = response_answer_revision_repo.get_latest(response_db, locked_answer.id)
                next_revision_number = (latest_rev.revision_number + 1) if latest_rev else 1
                existing_answer = locked_answer
        else:
            answer_row = locked_answer  # type: ignore[assignment]

        nonce = generate_nonce()
        aad = build_aad(
            crypto_version=ctx.envelope.crypto_version,
            envelope_id=answer_row.envelope_id,
            answer_id=answer_row.id,
            answer_locator=answer_locator,
            revision_id=revision_id,
            revision_number=next_revision_number,
        )
        ciphertext = encrypt_answer(plaintext, plaintext_dek, nonce, aad)

        # Step 8: Insert a new immutable revision
        revision = response_answer_revision_repo.create(
            response_db,
            answer_id=answer_row.id,
            envelope_id=ctx.envelope.id,
            revision_number=next_revision_number,
            nonce=nonce,
            ciphertext=ciphertext,
            client_mutation_id=client_mutation_id,
            revision_id=revision_id,
        )

        # Step 9: Update the latest pointer
        response_answer_revision_repo.update_latest_pointer(response_db, answer_row.id, revision.id)

        # Step 10: Commit the response transaction
        commit_with_err_handle(response_db, contexts=[])

        # Step 11: Insert core answer-saved analytics event
        # Step 12: Commit core transaction — failure is non-fatal
        try:
            event_repo.create_event(
                db,
                session_id=ctx.session.id,
                survey_version_id=ctx.survey_version.id,
                event_type="answer_saved",
                question_node_id=uuid.UUID(question_node_id),
            )
            commit_with_err_handle(db, contexts=[])
        except Exception:
            logger.warning("answer_save.analytics_event_failed", exc_info=True)
            db.rollback()

        return revision.id

    def record_question_viewed(
        self,
        db: Session,
        *,
        ctx: SessionContext,
        question_node_id: str,
    ) -> None:
        """Record a question-viewed analytics event. Failure does not block the respondent."""
        self._validate_question_in_version(db, ctx, question_node_id)
        try:
            event_repo.create_event(
                db,
                session_id=ctx.session.id,
                survey_version_id=ctx.survey_version.id,
                event_type="question_viewed",
                question_node_id=uuid.UUID(question_node_id),
            )
            commit_with_err_handle(db, contexts=[])
        except Exception:
            logger.warning("question_viewed.event_failed", exc_info=True)
            db.rollback()

    def _derive_answer_locator(self, ctx: SessionContext, question_node_id: str) -> bytes:
        enc = ctx.encryption_settings
        linkage_secret = get_linkage_secret(
            enc.linkage_secret_arn,
            region=enc.aws_region,
            access_key_id=enc.aws_access_key_id,
            secret_access_key=enc.aws_secret_access_key,
        )
        return derive_answer_locator(str(ctx.session.id), question_node_id, linkage_secret)

    def _get_or_unwrap_dek(self, ctx: SessionContext) -> bytes:
        if self._dek_cache is not None:
            cached = self._dek_cache.get(ctx.session_locator)
            if cached is not None:
                return cached

        enc = ctx.encryption_settings
        kms_context = {
            "session_locator": ctx.session_locator.hex(),
            "kms_context_version": str(_KMS_CONTEXT_VERSION),
        }
        plaintext_dek = unwrap_dek(
            ctx.envelope.wrapped_dek,
            ctx.envelope.kms_key_arn,
            kms_context,
            region=enc.aws_region,
            access_key_id=enc.aws_access_key_id,
            secret_access_key=enc.aws_secret_access_key,
        )

        if self._dek_cache is not None:
            self._dek_cache.put(ctx.session_locator, plaintext_dek)

        return plaintext_dek

    def _validate_question_in_version(
        self,
        db: Session,
        ctx: SessionContext,
        question_node_id: str,
    ) -> SurveyQuestion:
        question = db.scalar(
            select(SurveyQuestion).where(
                SurveyQuestion.survey_version_id == ctx.survey_version.id,
                SurveyQuestion.id == uuid.UUID(question_node_id),
            )
        )
        if question is None:
            raise QuestionNotInVersionError()
        return question
