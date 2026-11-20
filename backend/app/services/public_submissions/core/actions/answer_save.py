"""Persist self-describing answers in stable slots bound to document fields."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.crypto.answers import derive_slot_answer_locator, encrypt_answer_current
from app.crypto.models import AnswerContext, SubmissionSessionContext
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import AnswerSaveError, FieldNotInVersionError, SessionInvalidError
from app.logging.request_timing import request_timing
from app.repositories.core import submission_answer_slots
from app.repositories.core import submission_events as event_repo
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_answer_repo
from app.schema.models.results.service_results import AnswerSaveResult
from app.schema.models.survey_document.answers import AnswerData
from app.schema.models.survey_document.document import InputBlock
from app.schema.models.survey_document.fields import SurveyField
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.types import ClientMutationId, SurveyFieldUuid


def _field_for_session(
    session: SubmissionSession, ctx: SubmissionSessionContext, field_uuid: SurveyFieldUuid
) -> SurveyField:
    """Resolve one unambiguous field in the session's authoritative pinned version."""
    if (session.project_id, session.survey_id, session.survey_version_id) != (
        ctx.project_id,
        ctx.survey_id,
        ctx.survey_version_id,
    ):
        raise SessionInvalidError("Session context does not match its pinned survey version.")
    content = session.survey_version.content
    if content is None:
        raise FieldNotInVersionError()
    matches = [
        block.field
        for section in content.sections
        for block in section.blocks
        if isinstance(block, InputBlock) and block.field.uuid == field_uuid
    ]
    if len(matches) != 1:
        raise FieldNotInVersionError()
    return matches[0]


class AnswerSaveService:
    """Encrypt and persist validated answers for fields in active sessions."""

    def save_answer(
        self,
        db: Session,
        response_db: Session,
        *,
        ctx: SubmissionSessionContext,
        field_uuid: SurveyFieldUuid,
        answer: AnswerData,
        client_mutation_id: ClientMutationId,
    ) -> AnswerSaveResult:
        """Save one answered or cleared state under its stable session/field slot."""
        session = ssr.lock_for_update(db, ctx.session_id)
        if session is None:
            raise AnswerSaveError("Session disappeared during answer save.")
        if session.session_status != "in_progress":
            raise SessionInvalidError(f"Session is {session.session_status}.")
        request_timing.log("Session is locked for update")
        field = _field_for_session(session, ctx, field_uuid)
        slot = submission_answer_slots.get_or_create(
            db,
            submission_session_id=ctx.session_id,
            survey_version_id=ctx.survey_version_id,
            field_uuid=field.uuid,
            field_id=field.id,
        )
        request_timing.log("Answer slot is ready")
        locator = derive_slot_answer_locator(slot.id, ctx.linkage_key)
        context = AnswerContext(
            dek=ctx.plaintext_session_dek,
            crypto_version=ctx.crypto_version,
            envelope_id=ctx.envelope_id,
            answer_locator=locator,
        )
        encrypted = encrypt_answer_current(context=context, field_uuid=field.uuid, answer=answer)
        request_timing.log("Answer payload encrypted")

        # Keep the existing two-database ordering and locator derivation.
        commit_with_err_handle(db, contexts=[slot])
        saved = response_answer_repo.upsert_current(
            response_db,
            envelope_id=ctx.envelope_id,
            answer_locator=locator,
            nonce=encrypted.nonce,
            ciphertext=encrypted.ciphertext,
            client_mutation_id=client_mutation_id,
        )
        saved_at = saved.updated_at
        commit_with_err_handle(response_db, contexts=[])
        event_repo.record_event(
            db,
            session_id=ctx.session_id,
            survey_version_id=ctx.survey_version_id,
            event_type="answer_saved",
            field_uuid=field.uuid,
            log_label="answer_save.analytics",
        )
        return AnswerSaveResult(field_uuid=field.uuid, field_id=field.id, saved_at=saved_at)

    def record_field_viewed(self, db: Session, *, ctx: SubmissionSessionContext, field_uuid: SurveyFieldUuid) -> None:
        """Record a viewed event only for a field in the pinned session document."""
        session = ssr.get_by_id(db, ctx.session_id)
        if session is None or session.session_status != "in_progress":
            raise SessionInvalidError("Session is not active.")
        field = _field_for_session(session, ctx, field_uuid)
        event_repo.record_event(
            db,
            session_id=ctx.session_id,
            survey_version_id=ctx.survey_version_id,
            event_type="field_viewed",
            field_uuid=field.uuid,
            log_label="field_viewed",
        )
