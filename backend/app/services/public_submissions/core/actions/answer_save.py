"""Validate, encrypt, and persist the current answer for one session field.

See docs/project-knowledge/data/responses-and-encryption.md.
Also provides the field-viewed event helper.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import cast

from sqlalchemy.orm import Session

from app.crypto._internal.models import PlaintextAnswerValue
from app.crypto.answers import (
    derive_slot_answer_locator,
    encrypt_answer_current,
)
from app.crypto.models import AnswerContext, SubmissionSessionContext
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import (
    AnswerSaveError,
    FieldNotInDefinitionError,
    InvalidFieldAnswerError,
    SessionInvalidError,
)
from app.domain.survey_document_answer_validation import validate_field_answer
from app.logging.request_timing import request_timing
from app.repositories import surveys_repo
from app.repositories.core import submission_answer_slots
from app.repositories.core import submission_events as event_repo
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_answer_repo
from app.schema.api.content.common import FieldId
from app.schema.api.content.survey_document import (
    InputBlock,
    SurveyDefinition,
    SurveyDocumentAnswerValue,
    SurveyField,
)
from app.schema.enums import SubmissionAnswerState, SurveyResponseType
from app.services.results import AnswerSaveResult

logger = logging.getLogger(__name__)

AnswerValueInput = SurveyDocumentAnswerValue | None


def _answer_value_to_json(answer_value: AnswerValueInput) -> PlaintextAnswerValue:
    if isinstance(answer_value, date):
        return answer_value.isoformat()
    if isinstance(answer_value, list):
        return [*answer_value]
    return answer_value


def _find_field(definition: SurveyDefinition, field_id: FieldId) -> SurveyField:
    for section in definition.document.sections:
        for block in section.blocks:
            if isinstance(block, InputBlock) and block.field.id == field_id:
                return block.field
    raise FieldNotInDefinitionError()


class AnswerSaveService:
    """Encrypt and persist current survey answers for active sessions."""

    def save_answer(
        self,
        db: Session,
        response_db: Session,
        *,
        ctx: SubmissionSessionContext,
        field_id: FieldId,
        answer_state: SubmissionAnswerState,
        answer_value: AnswerValueInput,
        client_mutation_id: uuid.UUID,
    ) -> AnswerSaveResult:
        """Save the current answer for a field in the session's frozen definition."""
        locked_session = ssr.lock_for_update(db, ctx.session_id)
        if locked_session is None:
            raise AnswerSaveError("Session disappeared during answer save.")
        if locked_session.session_status != "in_progress":
            raise SessionInvalidError(f"Session is {locked_session.session_status}.")
        request_timing.log("Session is locked for update")

        version = surveys_repo.get_version_by_id(db, ctx.survey_version_id)
        if version is None:
            raise AnswerSaveError("Survey version disappeared during answer save.")
        definition = SurveyDefinition.model_validate(version.definition)
        field = _find_field(definition, field_id)

        validated_value: AnswerValueInput = None
        if answer_state == "answered":
            if answer_value is None:
                raise InvalidFieldAnswerError("Answered state requires a value.")
            validated_value = validate_field_answer(field, answer_value)
        elif answer_value is not None:
            raise InvalidFieldAnswerError("Cleared state cannot include a value.")

        slot = submission_answer_slots.get_or_create(
            db,
            submission_session_id=ctx.session_id,
            survey_version_id=ctx.survey_version_id,
            field_id=field_id,
        )
        request_timing.log("Answer slot is ready")

        answer_locator = derive_slot_answer_locator(slot.id, ctx.linkage_key)
        request_timing.log("Answer locator is derived")

        json_answer_value = _answer_value_to_json(validated_value)
        request_timing.log("Answer shape validated")

        answer_context = AnswerContext(
            dek=ctx.plaintext_session_dek,
            crypto_version=ctx.crypto_version,
            envelope_id=ctx.envelope_id,
            answer_locator=answer_locator,
        )
        encrypted = encrypt_answer_current(
            context=answer_context,
            field_id=field_id,
            answer_state=answer_state,
            answer_value=json_answer_value,
        )
        request_timing.log("Answer payload encrypted")

        # Commit the core answer slot immediately before updating the response DB.
        commit_with_err_handle(db, contexts=[slot])
        request_timing.log("Answer slot committed")

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
            field_id=field_id,
            log_label="answer_save.analytics",
        )

        return AnswerSaveResult(
            field_key=field.key,
            response_type=cast(SurveyResponseType, field.response.type),
            value=validated_value,
        )

    def record_field_viewed(
        self,
        db: Session,
        *,
        ctx: SubmissionSessionContext,
        field_id: FieldId,
    ) -> None:
        """Record a field-viewed event after resolving the canonical field id."""
        version = surveys_repo.get_version_by_id(db, ctx.survey_version_id)
        if version is None:
            raise FieldNotInDefinitionError()
        definition = SurveyDefinition.model_validate(version.definition)
        _find_field(definition, field_id)
        event_repo.record_event(
            db,
            session_id=ctx.session_id,
            survey_version_id=ctx.survey_version_id,
            event_type="field_viewed",
            field_id=field_id,
            log_label="field_viewed",
        )
