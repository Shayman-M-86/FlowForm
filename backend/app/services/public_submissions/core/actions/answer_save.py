"""Answer save orchestration following the exact 12-step sequence from doc 03.

Also provides the question-viewed event helper.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, cast
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crypto.answers import (
    derive_session_answer_locator,
    encrypt_answer_revision,
)
from app.crypto.models import RevisionContext, SessionContext
from app.crypto.session_key import start_plaintext_session_key_load
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import AnswerSaveError, QuestionNotInVersionError, SessionInvalidError
from app.domain.survey_answer_validation import validate_answer
from app.logging.request_timing import request_timing
from app.repositories import content_repo
from app.repositories.core import submission_events as event_repo
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_answer_repo, response_answer_revision_repo
from app.schema.api.submission_sessions.answer_payload import SubmissionAnswerValue
from app.schema.enums import SubmissionAnswerState

logger = logging.getLogger(__name__)

AnswerValueInput = SubmissionAnswerValue | dict[str, Any] | None


def _answer_value_to_json(answer_value: AnswerValueInput) -> dict[str, Any] | None:
    if answer_value is None:
        return None
    if isinstance(answer_value, BaseModel):
        return cast(dict[str, Any], answer_value.model_dump(mode="json"))
    return answer_value


class AnswerSaveService:
    """Service for orchestrating the 12-step answer save sequence.

    Handles encryption, validation, and persistence of survey answers with
    proper session management and duplicate detection.
    """

    def save_answer(
        self,
        db: Session,
        response_db: Session,
        *,
        ctx: SessionContext,
        question_node_id: UUID,
        answer_state: SubmissionAnswerState,
        answer_value: AnswerValueInput,
        client_mutation_id: uuid.UUID,
    ) -> int:
        """Execute the 12-step answer save sequence. Returns the revision number."""
        # Step 1: Validate and lock the current session
        locked_session = ssr.lock_for_update(db, ctx.session_id)
        if locked_session is None:
            raise AnswerSaveError("Session disappeared during answer save.")
        if locked_session.session_status != "in_progress":
            raise SessionInvalidError(f"Session is {locked_session.session_status}.")
        request_timing.log("Session is locked for update")

        # Step 2: Check mutation ID — before any row lock on the logical answer
        answer_locator = derive_session_answer_locator(ctx, question_node_id)
        request_timing.log("Answer locator is derived")
        existing_answer = response_answer_repo.get_by_locator(response_db, ctx.envelope_id, answer_locator)
        if existing_answer is not None:
            dup_revision = response_answer_revision_repo.get_by_mutation_id(
                response_db, existing_answer.id, client_mutation_id
            )
            if dup_revision is not None:
                return dup_revision.revision_number
        request_timing.log("Mutation ID checked for duplicates")

        # Step 3: Validate the answer against the frozen survey question node
        question = content_repo.get_question_node(db, ctx.survey_version_id, question_node_id)
        if question is None:
            raise QuestionNotInVersionError()

        # Step 3b: Validate answer shape against the frozen question definition
        json_answer_value = _answer_value_to_json(answer_value)
        if answer_state != "cleared" and json_answer_value is not None:
            validate_answer(question.question_schema, json_answer_value)
        request_timing.log("Answer shape validated")

        # Step 4-6: Start session-key resolution after dedupe and validation.
        resolve_session_key = start_plaintext_session_key_load(
            db,
            response_db,
            context=ctx,
        )
        request_timing.log("Session key resolver is ready")

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
        request_timing.log("Revision ID generated")
        if existing_answer is None:
            # First save: create logical answer row with the revision we're about to insert
            answer_row, created = response_answer_repo.get_or_create(
                response_db,
                envelope_id=ctx.envelope_id,
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
                    return dup_revision.revision_number
                locked_answer = response_answer_repo.lock_for_update(response_db, answer_row.id)
                if locked_answer is None:
                    raise AnswerSaveError("Logical answer row disappeared after race.")
                latest_rev = response_answer_revision_repo.get_latest(response_db, locked_answer.id)
                next_revision_number = (latest_rev.revision_number + 1) if latest_rev else 1
                existing_answer = locked_answer
        else:
            answer_row = locked_answer  # type: ignore[assignment]
        request_timing.log("Logical answer row is ready with next revision number")

        # Step 7: Encrypt the answer payload
        revision_context = RevisionContext(
            dek=resolve_session_key(),
            crypto_version=ctx.crypto_version,
            envelope_id=ctx.envelope_id,
            answer_id=answer_row.id,
            answer_locator=answer_locator,
            revision_id=revision_id,
            revision_number=next_revision_number,
        )
        encrypted = encrypt_answer_revision(
            context=revision_context,
            question_node_id=question_node_id,
            answer_state=answer_state,
            answer_value=answer_value,
        )
        request_timing.log("Answer payload encrypted")

        # Step 8: Insert a new immutable revision
        revision = response_answer_revision_repo.create(
            response_db,
            answer_id=answer_row.id,
            envelope_id=ctx.envelope_id,
            revision_number=next_revision_number,
            nonce=encrypted.nonce,
            ciphertext=encrypted.ciphertext,
            client_mutation_id=client_mutation_id,
            revision_id=revision_id,
        )

        # Step 9: Update the latest pointer
        response_answer_revision_repo.update_latest_pointer(response_db, answer_row.id, revision.id)

        # Step 10: Commit the response transaction
        commit_with_err_handle(response_db, contexts=[])
        request_timing.log("Response transaction committed")

        # Step 11-12: Insert and commit core analytics event (non-fatal)
        event_repo.record_event(
            db,
            session_id=ctx.session_id,
            survey_version_id=ctx.survey_version_id,
            event_type="answer_saved",
            question_node_id=question_node_id,
            log_label="answer_save.analytics",
        )

        return revision.revision_number

    def record_question_viewed(
        self,
        db: Session,
        *,
        ctx: SessionContext,
        question_node_id: UUID,
    ) -> None:
        """Record a question-viewed analytics event. Failure does not block the respondent."""
        if content_repo.get_question_node(db, ctx.survey_version_id, question_node_id) is None:
            raise QuestionNotInVersionError()
        event_repo.record_event(
            db,
            session_id=ctx.session_id,
            survey_version_id=ctx.survey_version_id,
            event_type="question_viewed",
            question_node_id=question_node_id,
            log_label="question_viewed",
        )
