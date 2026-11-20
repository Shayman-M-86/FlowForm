"""Assemble field-answer result trees from each session's pinned document."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Mapping
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.cache import get_app_cache
from app.crypto._internal.client_extension import get_crypto_clients
from app.crypto._internal.errors import PayloadDecodeError
from app.crypto._internal.models import DecryptedAnswerPayload
from app.repositories.core import submission_answer_slots, submission_events
from app.repositories.core import submission_sessions as ssr
from app.schema.models.results.answer_results import AnswerSlotResult, SessionEventResult
from app.schema.models.results.service_results import SessionTreeResult
from app.schema.orm.core.submission_answer_slot import SubmissionAnswerSlot
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.response.response_answer import ResponseAnswer
from app.schema.types import AnswerLocator, SubjectId, SurveyId
from app.services.admin_results.core.decryption import resolve_and_decrypt_answers
from app.services.admin_results.core.field_meta import FieldMap, build_field_map

if TYPE_CHECKING:
    from app.cache import AppCache
    from app.crypto._internal.client_extension import CryptoClients

logger = logging.getLogger(__name__)


class SessionTreeBuilder:
    """Build metadata-only or decrypted trees without inspecting legacy question families."""

    def __init__(self, *, cache: AppCache | None = None, clients: CryptoClients | None = None) -> None:
        self._cache = cache or get_app_cache()
        self._clients = clients or get_crypto_clients()

    def group_sessions_by_subject(
        self, db: Session, *, survey_id: SurveyId, subject_ids: list[SubjectId]
    ) -> dict[SubjectId, list[SubmissionSession]]:
        """Group sessions by their canonical subject identity."""
        sessions = ssr.list_by_subjects(db, survey_id=survey_id, project_subject_ids=subject_ids)
        grouped: dict[SubjectId, list[SubmissionSession]] = defaultdict(list)
        for session in sessions:
            if session.project_subject_id is not None:
                grouped[session.project_subject_id].append(session)
        return grouped

    def build_session_result(
        self,
        db: Session,
        response_db: Session,
        *,
        session: SubmissionSession,
        include_decrypted_answer_values: bool,
        include_events: bool,
    ) -> SessionTreeResult:
        """Use the pinned document for metadata and the encrypted payload for answer data."""
        events = self.load_events(db, session=session) if include_events else None
        slots = submission_answer_slots.list_by_session(db, submission_session_id=session.id)
        if not slots:
            return SessionTreeResult(session=session, answers=[], events=events)
        fields = build_field_map(session.survey_version.content)
        resolved = resolve_and_decrypt_answers(
            db,
            response_db,
            session=session,
            slots=slots,
            include_decrypted_answer_values=include_decrypted_answer_values,
            cache=self._cache,
            clients=self._clients,
        )
        answers = [
            build_answer_slot_result(
                slot,
                locator=resolved.locators[slot.id],
                found=resolved.found,
                decrypted_by_locator=resolved.decrypted_by_locator,
                fields=fields,
            )
            for slot in slots
        ]
        return SessionTreeResult(session=session, answers=answers, events=events)

    def load_events(self, db: Session, *, session: SubmissionSession) -> list[SessionEventResult] | None:
        """Return field-based timeline events; optional analytics remain best effort."""
        try:
            return [
                SessionEventResult(
                    event_type=event.event_type, field_uuid=event.field_uuid, received_at=event.received_at
                )
                for event in submission_events.list_by_session(db, session_id=session.id)
            ]
        except Exception:
            logger.exception("admin_results.events_load_failed session_id=%s", session.id)
            return None


def build_answer_slot_result(
    slot: SubmissionAnswerSlot,
    *,
    locator: AnswerLocator,
    found: Mapping[AnswerLocator, ResponseAnswer],
    decrypted_by_locator: Mapping[AnswerLocator, DecryptedAnswerPayload],
    fields: FieldMap,
) -> AnswerSlotResult:
    """Combine existing field metadata with already-validated decrypted answer data."""
    field = fields.get(slot.field_uuid)
    payload = decrypted_by_locator.get(locator)
    if payload is not None and payload.field_uuid != slot.field_uuid:
        raise PayloadDecodeError("Decrypted field identity does not match the answer slot.")
    return AnswerSlotResult(
        field_uuid=slot.field_uuid,
        field_id=field.id if field is not None else slot.field_id,
        has_encrypted_answer=locator in found,
        decrypted=payload is not None,
        state=payload.state if payload is not None else None,
        answer_spec=payload.answer_spec if payload is not None else None,
        answer_value=payload.answer_value if payload is not None and payload.state == "answered" else None,
        field=field,
    )
