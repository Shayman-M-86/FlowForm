from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.enums import SubmissionEventType
from app.schema.orm.core.submission_session import SubmissionEvent

logger = logging.getLogger(__name__)


def create_event(
    db: Session,
    *,
    session_id: uuid.UUID,
    survey_version_id: int,
    event_type: SubmissionEventType,
    question_node_id: uuid.UUID | None = None,
) -> SubmissionEvent:
    event = SubmissionEvent(
        session_id=session_id,
        survey_version_id=survey_version_id,
        event_type=event_type,
        question_node_id=question_node_id,
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
    log_label: str = "submission_event",
) -> None:
    """Insert and commit an analytics event. Failure is logged and swallowed — never raises."""
    try:
        create_event(
            db,
            session_id=session_id,
            survey_version_id=survey_version_id,
            event_type=event_type,
            question_node_id=question_node_id,
        )
        db.commit()
    except Exception:
        logger.warning(f"{log_label}.event_failed", exc_info=True)
        db.rollback()
