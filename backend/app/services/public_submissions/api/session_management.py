"""Respondent submission-session lifecycle: start, answer, event, complete.

API-facing entry point. Routes in api/v1/public.py call this service directly.
Start delegates to core/session_starter.py. Complete delegates to
core/completion.py. Answer/event are phase placeholders.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schema.api.requests.submission_sessions import (
    SaveSubmissionSessionAnswerRequest,
    StartSubmissionSessionRequest,
    SubmissionSessionEventRequest,
)
from app.schema.api.responses.submission_sessions import StartSubmissionSessionResponse
from app.schema.orm.core.user import User
from app.services.public_submissions.core.actions.completion import (
    CompletionResult,
    CompletionService,
)
from app.services.public_submissions.core.actions.session_starter import SessionStarter
from app.services.public_submissions.core.shared.session_loader import load_current_session


class SessionManagementService:
    """Full respondent session lifecycle."""

    def __init__(
        self,
        *,
        session_starter: SessionStarter | None = None,
        completion_service: CompletionService | None = None,
    ) -> None:
        self._session_starter = session_starter or SessionStarter()
        self._completion_service = completion_service or CompletionService()

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
        raw_resume_token: str,
    ) -> CompletionResult:
        """Complete a respondent session.

        Loads the session from the browser resume token, then delegates to
        CompletionService for the completion state transition.
        """
        ctx = load_current_session(db, response_db, raw_resume_token, allow_completed=True)
        return self._completion_service.complete_session(db, response_db, ctx=ctx)

    # ------------------------------------------------------------------
    # Phase placeholders — mirror current route stubs in public.py.
    # ------------------------------------------------------------------

    def save_answer(self, db: Session, *, payload: SaveSubmissionSessionAnswerRequest) -> None:
        """Save a respondent answer.

        TODO(phase4): validate against the frozen survey version and create
        encrypted response answer revisions.
        """
        raise NotImplementedError

    def record_event(self, db: Session, *, payload: SubmissionSessionEventRequest) -> None:
        """Record a respondent session event.

        TODO(phase3): persist core-side analytics events; event write failures
        stay secondary to the respondent flow.
        """
        raise NotImplementedError
