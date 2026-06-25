"""Respondent submission-session lifecycle: start, answer, event, complete.

API-facing entry point. Routes in api/v1/respondent/ call this service directly.
Start delegates to core/session_starter.py. Answer delegates to
core/answer_save.py. Complete delegates to core/completion.py.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.errors import SessionNotFoundError
from app.schema.api.requests.submission_sessions import (
    StartSubmissionSessionRequest,
)
from app.schema.api.responses.submission_sessions import StartSubmissionSessionResponse
from app.schema.api.submission_sessions.answer_payload import SubmissionAnswerValue
from app.schema.enums import SubmissionAnswerState
from app.schema.orm.core.user import User
from app.services.public_submissions.core.actions.answer_save import AnswerSaveService
from app.services.public_submissions.core.actions.completion import (
    CompletionResult,
    CompletionService,
)
from app.services.public_submissions.core.actions.session_starter import SessionStarter
from app.services.public_submissions.core.session_loader import load_current_session


class SessionManagementService:
    """Full respondent session lifecycle."""

    def __init__(
        self,
        *,
        session_starter: SessionStarter | None = None,
        completion_service: CompletionService | None = None,
        answer_save_service: AnswerSaveService | None = None,
    ) -> None:
        self._session_starter = session_starter or SessionStarter()
        self._completion_service = completion_service or CompletionService()
        self._answer_save_service = answer_save_service or AnswerSaveService()

    def start_session(
        self,
        db: Session,
        response_db: Session,
        *,
        payload: StartSubmissionSessionRequest,
        actor: User | None,
        recognition_token: str | None = None,
    ) -> tuple[StartSubmissionSessionResponse, str, str | None]:
        """Start a respondent submission session.

        Returns (session_response, raw_browser_session_token, raw_recognition_token).
        The route sets the browser-session and recognition cookies from the raw tokens.
        """
        return self._session_starter.start(
            db, response_db, payload=payload, actor=actor, recognition_token=recognition_token
        )

    def complete_session(
        self,
        db: Session,
        response_db: Session,
        *,
        raw_resume_token: str | None,
    ) -> CompletionResult:
        """Complete a respondent session.

        Loads the session from the browser resume token, then delegates to
        CompletionService for the completion state transition.
        """
        if raw_resume_token is None:
            raise SessionNotFoundError()
        ctx = load_current_session(db, response_db, raw_resume_token, allow_completed=True)
        return self._completion_service.complete_session(db, response_db, ctx=ctx)

    def save_answer(
        self,
        db: Session,
        response_db: Session,
        *,
        raw_resume_token: str | None,
        question_node_id: UUID,
        answer_state: SubmissionAnswerState,
        answer_value: SubmissionAnswerValue | dict[str, Any] | None,
        client_mutation_id: UUID,
    ) -> int:
        """Save a respondent answer. Returns the revision number."""
        if raw_resume_token is None:
            raise SessionNotFoundError()
        ctx = load_current_session(db, response_db, raw_resume_token)
        return self._answer_save_service.save_answer(
            db,
            response_db,
            ctx=ctx,
            question_node_id=question_node_id,
            answer_state=answer_state,
            answer_value=answer_value,
            client_mutation_id=client_mutation_id,
        )

    def record_question_viewed(
        self,
        db: Session,
        response_db: Session,
        *,
        raw_resume_token: str | None,
        question_node_id: UUID,
    ) -> None:
        """Record a question-viewed analytics event."""
        if raw_resume_token is None:
            raise SessionNotFoundError()
        ctx = load_current_session(db, response_db, raw_resume_token)
        self._answer_save_service.record_question_viewed(
            db,
            ctx=ctx,
            question_node_id=question_node_id,
        )
