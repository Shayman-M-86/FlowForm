from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.enums import SubmissionEventType
from app.schema.orm.core.submission_session import SubmissionEvent

logger = logging.getLogger(__name__)


def _normalise_event_metadata(
    event_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a JSON object for submission_events.metadata.

    The database check constraint requires metadata to be a JSON object.
    None would be stored as JSON null, which violates that constraint.
    """
    if event_metadata is None:
        return {}

    return event_metadata


def create_event(
    db: Session,
    *,
    session_id: uuid.UUID,
    survey_version_id: int,
    event_type: SubmissionEventType,
    question_node_id: uuid.UUID | None = None,
    event_metadata: dict[str, Any] | None = None,
) -> SubmissionEvent:
    """Create and flush one submission event.

    Does not commit. The caller owns the transaction.
    """
    event = SubmissionEvent(
        session_id=session_id,
        survey_version_id=survey_version_id,
        event_type=event_type,
        question_node_id=question_node_id,
        event_metadata=_normalise_event_metadata(event_metadata),
    )

    db.add(event)
    flush_with_err_handle(db, contexts=[event])
    return event


def record_event(
    db: Session,
    *,
    session_id: uuid.UUID,
    survey_version_id: int,
    event_type: SubmissionEventType,
    question_node_id: uuid.UUID | None = None,
    event_metadata: dict[str, Any] | None = None,
    log_label: str = "submission_event",
) -> None:
    """Insert and commit an analytics event.

    Best-effort only. Failure is logged and swallowed.
    """
    try:
        create_event(
            db,
            session_id=session_id,
            survey_version_id=survey_version_id,
            event_type=event_type,
            question_node_id=question_node_id,
            event_metadata=event_metadata,
        )
        db.commit()

    except SQLAlchemyError:
        db.rollback()
        logger.warning("%s.event_failed", log_label, exc_info=True)

    except Exception:
        db.rollback()
        logger.exception("%s.unexpected_event_failure", log_label)


def list_by_session(db: Session, *, session_id: uuid.UUID) -> list[SubmissionEvent]:
    """Return all timeline events for one session, oldest first."""
    return list(
        db.scalars(
            select(SubmissionEvent)
            .where(SubmissionEvent.session_id == session_id)
            .order_by(SubmissionEvent.received_at)
        ).all()
    )
