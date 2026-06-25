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

from app.crypto import build_aad, get_crypto_services
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import AnswerSaveError, QuestionNotInVersionError, SessionInvalidError
from app.domain.survey_answer_validation import validate_answer
from app.logging.request_timing import request_timing
from app.repositories import content_repo
from app.repositories.core import submission_events as event_repo
from app.repositories.core import submission_sessions as ssr
from app.repositories.core import survey_encryption_keys as survey_key_repo
from app.repositories.response import response_answer_repo, response_answer_revision_repo
from app.schema.api.submission_sessions.answer_payload import SubmissionAnswerValue
from app.schema.enums import SubmissionAnswerState
from app.services.public_submissions.core.shared.session_crypto import load_plaintext_session_dek
from app.services.public_submissions.core.shared.session_loader import SessionContext

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
        crypto = get_crypto_services()

        branch_key_resolver = None
        if crypto.survey_branch_key_service is not None:
            survey_key = survey_key_repo.get_by_project_survey(
                db,
                project_id=ctx.session.project_id,
                survey_id=ctx.session.survey_id,
            )
            if survey_key is not None:
                branch_key_resolver = (
                    crypto.survey_branch_key_service.prefetch_plaintext_key(
                        survey_key,
                    )
                )
        request_timing.log("Crypto service is loaded ")

        # Step 1: Validate and lock the current session
        locked_session = ssr.lock_for_update(db, ctx.session.id)
        if locked_session is None:
            raise AnswerSaveError("Session disappeared during answer save.")
        if locked_session.session_status != "in_progress":
            raise SessionInvalidError(f"Session is {locked_session.session_status}.")
        request_timing.log("Session is locked for update")

        # Step 2: Check mutation ID — before any row lock on the logical answer
        answer_locator = crypto.locator_service.answer_locator(
            ctx.session.id,
            question_node_id,
            ctx.session.linkage_key_version,
            db,
            linkage_key=ctx.linkage_key,
        )
        request_timing.log("Answer locator is derived")
        existing_answer = response_answer_repo.get_by_locator(response_db, ctx.envelope.id, answer_locator)
        if existing_answer is not None:
            dup_revision = response_answer_revision_repo.get_by_mutation_id(
                response_db, existing_answer.id, client_mutation_id
            )
            if dup_revision is not None:
                return dup_revision.revision_number
        request_timing.log("Mutation ID checked for duplicates")

        # Step 3: Validate the answer against the frozen survey question node
        question = content_repo.get_question_node(db, ctx.survey_version.id, question_node_id)
        if question is None:
            raise QuestionNotInVersionError()

        # Step 3b: Validate answer shape against the frozen question definition
        json_answer_value = _answer_value_to_json(answer_value)
        if answer_state != "cleared" and json_answer_value is not None:
            validate_answer(question.question_schema, json_answer_value)
        request_timing.log("Answer shape validated")

        # Step 4: Derive session locator and answer locator (locator already derived)
        # Step 5: Load the response envelope (already in ctx)

        # Step 6: Load plaintext DEK from cache; on miss, unwrap locally through the survey branch key.
        plaintext_dek = load_plaintext_session_dek(
            db,
            session=locked_session,
            session_locator=ctx.session_locator,
            envelope=ctx.envelope,
            crypto=crypto,
            prefetched_branch_key_loader=branch_key_resolver,
        )
        request_timing.log("Plaintext DEK loaded")

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
        aad = build_aad(
            crypto_version=ctx.envelope.crypto_version,
            envelope_id=answer_row.envelope_id,
            answer_id=answer_row.id,
            answer_locator=answer_locator,
            revision_id=revision_id,
            revision_number=next_revision_number,
        )
        request_timing.log("Answer payload encrypted")
        encrypted = crypto.answer_crypto_service.encrypt(
            dek=plaintext_dek,
            question_node_id=question_node_id,
            answer_state=answer_state,
            answer_value=answer_value,
            aad=aad,
        )

        # Step 8: Insert a new immutable revision
        revision = response_answer_revision_repo.create(
            response_db,
            answer_id=answer_row.id,
            envelope_id=ctx.envelope.id,
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
            session_id=ctx.session.id,
            survey_version_id=ctx.survey_version.id,
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
        if content_repo.get_question_node(db, ctx.survey_version.id, question_node_id) is None:
            raise QuestionNotInVersionError()
        event_repo.record_event(
            db,
            session_id=ctx.session.id,
            survey_version_id=ctx.survey_version.id,
            event_type="question_viewed",
            question_node_id=question_node_id,
            log_label="question_viewed",
        )
