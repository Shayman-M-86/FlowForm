"""Session/subject tree assembly for admin results.

``SessionTreeBuilder`` turns submission sessions into result trees: per-slot
answer results (optionally decrypted) plus an optional event timeline. It holds
the cache and crypto clients and delegates decryption to ``core.decryption`` and
metadata lookups to ``core.field_meta``.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.cache import get_app_cache
from app.crypto._internal.client_extension import get_crypto_clients
from app.crypto.models import AnswerLocator
from app.repositories import surveys_repo
from app.repositories.core import submission_answer_slots, submission_events
from app.repositories.core import submission_sessions as ssr
from app.schema.api.content.survey_document import (
    SurveyDefinition,
    SurveyDocumentAnswerValue,
    SurveyField,
    parse_survey_document_answer_value,
)
from app.schema.enums import SubmissionAnswerState
from app.schema.orm.core.submission_answer_slot import SubmissionAnswerSlot
from app.schema.orm.core.submission_session import SubmissionSession
from app.services.admin_results.core.decryption import resolve_and_decrypt_answers
from app.services.admin_results.core.field_meta import build_field_map
from app.services.results import (
    AnswerSlotResult,
    SessionEventResult,
    SessionTreeResult,
)

if TYPE_CHECKING:
    from app.cache import AppCache
    from app.crypto._internal.client_extension import CryptoClients

logger = logging.getLogger(__name__)


class SessionTreeBuilder:
    """Assemble session result trees, optionally decrypting answer values."""

    def __init__(
        self,
        *,
        cache: AppCache | None = None,
        clients: CryptoClients | None = None,
    ) -> None:
        self._cache = cache or get_app_cache()
        self._clients = clients or get_crypto_clients()

    def group_sessions_by_subject(
        self,
        db: Session,
        *,
        survey_id: int,
        subject_ids: list[UUID],
    ) -> dict[UUID, list[SubmissionSession]]:
        """Group this survey's sessions for the given subjects by subject id."""
        sessions = ssr.list_by_subjects(db, survey_id=survey_id, project_subject_ids=subject_ids)
        grouped: dict[UUID, list[SubmissionSession]] = defaultdict(list)
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
        """Build one session's answer-slot results, optionally decrypted, with optional events."""
        events = self.load_events(db, session=session) if include_events else None

        slots = submission_answer_slots.list_by_session(db, submission_session_id=session.id)
        if not slots:
            return SessionTreeResult(session=session, answers=[], events=events)

        version = surveys_repo.get_version_by_id(db, session.survey_version_id)
        if version is None:
            raise ValueError("The session's frozen survey version is missing.")
        fields = build_field_map(SurveyDefinition.model_validate(version.definition))

        resolved = resolve_and_decrypt_answers(
            db,
            response_db,
            session=session,
            slots=slots,
            include_decrypted_answer_values=include_decrypted_answer_values,
            cache=self._cache,
            clients=self._clients,
        )

        answer_results = [
            build_answer_slot_result(
                slot,
                locator=resolved.locators[slot.id],
                found=resolved.found,
                decrypted_by_locator=resolved.decrypted_by_locator,
                field=fields[slot.field_id],
            )
            for slot in slots
        ]
        return SessionTreeResult(session=session, answers=answer_results, events=events)

    def load_events(self, db: Session, *, session: SubmissionSession) -> list[SessionEventResult] | None:
        """Load timeline events for a session. Failures are logged and swallowed."""
        try:
            events = submission_events.list_by_session(db, session_id=session.id)
        except Exception:
            logger.exception("admin_results.events_load_failed session_id=%s", session.id)
            return None
        return [
            SessionEventResult(
                event_type=e.event_type,
                field_id=e.field_id,
                received_at=e.received_at,
            )
            for e in events
        ]


def build_answer_slot_result(
    slot: SubmissionAnswerSlot,
    *,
    locator: AnswerLocator,
    found: dict[bytes, Any],
    decrypted_by_locator: dict[bytes, Any],
    field: SurveyField,
) -> AnswerSlotResult:
    """Build one answer-slot result, resolving its decrypted value when present."""
    has_encrypted_answer = bytes(locator) in found
    decrypted_payload = decrypted_by_locator.get(bytes(locator))

    answer_state: SubmissionAnswerState | None = None
    answer_value: SurveyDocumentAnswerValue | None = None
    if decrypted_payload is not None:
        if decrypted_payload.field_id != slot.field_id:
            raise ValueError("Decrypted answer does not match its field slot.")
        answer_state = decrypted_payload.answer_state
        if answer_state == "answered":
            answer_value = parse_survey_document_answer_value(field.response.type, decrypted_payload.answer_value)

    return AnswerSlotResult(
        slot_id=slot.id,
        field_id=slot.field_id,
        field_key=field.key,
        response_type=field.response.type,
        has_encrypted_answer=has_encrypted_answer,
        decrypted=decrypted_payload is not None,
        answer_state=answer_state,
        answer_value=answer_value,
    )
