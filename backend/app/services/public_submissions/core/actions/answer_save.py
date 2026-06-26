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
    derive_slot_answer_locator,
    encrypt_answer_current,
)
from app.crypto.models import AnswerContext, SessionContext
from app.crypto.session_key import start_plaintext_session_key_load
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import AnswerSaveError, QuestionNotInVersionError, SessionInvalidError
from app.domain.survey_answer_validation import validate_answer
from app.logging.request_timing import request_timing
from app.repositories import content_repo
from app.repositories.core import submission_answer_slots, submission_events as event_repo
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_answer_repo
from app.schema.api.submission_sessions.answer_payload import SubmissionAnswerValue
from app.schema.enums import SubmissionAnswerState
from app.services.results import AnswerSaveResult

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
    ) -> AnswerSaveResult:
        """Save the current answer for a session/question slot."""
        locked_session = ssr.lock_for_update(db, ctx.session_id)
        if locked_session is None:
            raise AnswerSaveError("Session disappeared during answer save.")
        if locked_session.session_status != "in_progress":
            raise SessionInvalidError(f"Session is {locked_session.session_status}.")
        request_timing.log("Session is locked for update")

        question = content_repo.get_question_node(db, ctx.survey_version_id, question_node_id)
        if question is None:
            raise QuestionNotInVersionError()

        slot = submission_answer_slots.get_or_create(
            db,
            submission_session_id=ctx.session_id,
            survey_version_id=ctx.survey_version_id,
            question_node_id=question_node_id,
            question_key=question.question_key,
        )
        request_timing.log("Answer slot is ready")

        answer_locator = derive_slot_answer_locator(slot.id, ctx.linkage_key)
        request_timing.log("Answer locator is derived")

        json_answer_value = _answer_value_to_json(answer_value)
        if answer_state != "cleared" and json_answer_value is not None:
            validate_answer(question.question_schema, json_answer_value)
        request_timing.log("Answer shape validated")

        resolve_session_key = start_plaintext_session_key_load(
            db,
            response_db,
            context=ctx,
        )
        request_timing.log("Session key resolver is ready")

        answer_context = AnswerContext(
            dek=resolve_session_key(),
            crypto_version=ctx.crypto_version,
            envelope_id=ctx.envelope_id,
            answer_locator=answer_locator,
        )
        encrypted = encrypt_answer_current(
            context=answer_context,
            question_node_id=question_node_id,
            answer_state=answer_state,
            answer_value=answer_value,
        )
        request_timing.log("Answer payload encrypted")

        response_answer_repo.upsert_current(
            response_db,
            envelope_id=ctx.envelope_id,
            answer_locator=answer_locator,
            nonce=encrypted.nonce,
            ciphertext=encrypted.ciphertext,
            client_mutation_id=client_mutation_id,
        )

        commit_with_err_handle(response_db, contexts=[])
        request_timing.log("Response transaction committed")

        event_repo.record_event(
            db,
            session_id=ctx.session_id,
            survey_version_id=ctx.survey_version_id,
            event_type="answer_saved",
            question_node_id=question_node_id,
            log_label="answer_save.analytics",
        )

        return AnswerSaveResult(node_key=question.question_key)

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
