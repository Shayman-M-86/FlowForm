"""Session completion service.

Marks an in-progress session as completed. Completion is a state transition;
answers are validated when saved, before encryption and persistence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.extensions import app_cache
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import SessionInvalidError
from app.repositories.core import submission_events as event_repo
from app.repositories.core import submission_sessions as ssr
from app.services.public_submissions.core.shared.session_loader import SessionContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CompletionResult:
    """Outcome returned to the caller on successful completion."""

    session_id: UUID
    status: str
    completed_at: datetime


class CompletionService:
    """Orchestrates session completion as a core status transition."""

    def __init__(self, **_: object) -> None:
        """Accept legacy dependency kwargs; completion no longer decrypts answers."""

    def complete_session(
        self,
        db: Session,
        response_db: Session,
        *,
        ctx: SessionContext,
    ) -> CompletionResult:
        """Complete a session by moving it from in-progress to completed."""
        _ = response_db

        # Lock the session for mutation
        locked_session = ssr.lock_for_update(db, ctx.session.id)
        if locked_session is None:
            raise SessionInvalidError("Session disappeared during completion.")
        if locked_session.session_status != "in_progress":
            raise SessionInvalidError(f"Session is {locked_session.session_status}.")

        # Mark session completed. Use a timestamp that satisfies the DB invariant
        # even when app and database clocks differ slightly.
        completed_at = max(datetime.now(UTC), locked_session.started_at)
        ssr.mark_completed(db, submission_session=locked_session, completed_at=completed_at)

        # Insert completion event — non-fatal on failure
        try:
            event_repo.create_event(
                db,
                session_id=ctx.session.id,
                survey_version_id=ctx.survey_version.id,
                event_type="session_completed",
            )
        except Exception:
            logger.warning("completion.event_create_failed", exc_info=True)

        commit_with_err_handle(db, contexts=[])

        app_cache.sessions.write_context.evict(ctx.session.browser_session_token_hash)

        return CompletionResult(
            session_id=ctx.session.id,
            status="completed",
            completed_at=completed_at,
        )
