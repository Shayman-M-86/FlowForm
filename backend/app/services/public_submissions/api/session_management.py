"""Respondent submission-session lifecycle: start, answer, event, complete.

API-facing entry point. Routes in api/v1/public.py call this service directly.
Start delegates to core/session_starter.py. Answer/event/complete are phase
placeholders that mirror the current route stubs until the encrypted response
pipeline lands.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.schema.api.requests.submission_sessions import (
    SaveSubmissionSessionAnswerRequest,
    StartSubmissionSessionRequest,
    SubmissionSessionEventRequest,
)
from app.schema.api.responses.submission_sessions import PublicSubmissionSessionResponses
from app.schema.orm.core.user import User
from app.services.public_submissions.core.session_starter import SessionStarter


class SessionManagementService:
    """Full respondent session lifecycle."""

    def __init__(self, *, session_starter: SessionStarter | None = None) -> None:
        self._session_starter = session_starter or SessionStarter()

    def start_session(
        self,
        db: Session,
        *,
        payload: StartSubmissionSessionRequest,
        actor: User | None,
        recognition_token: str | None = None,
    ) -> tuple[PublicSubmissionSessionResponses, str, str | None]:
        """Start a respondent submission session.

        Returns (session_response, raw_browser_session_token, raw_recognition_token).
        The route sets the browser-session and recognition cookies from the raw tokens.
        """
        return self._session_starter.start(
            db, payload=payload, actor=actor, recognition_token=recognition_token
        )

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

    def complete_session(self, db: Session) -> None:
        """Complete a respondent session.

        TODO(phase5): complete the core session idempotently and reject later
        answer edits.
        """
        raise NotImplementedError
