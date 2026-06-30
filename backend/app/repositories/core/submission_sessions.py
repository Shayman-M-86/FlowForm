from __future__ import annotations

import hashlib
import secrets
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.enums import SubmissionSessionStatus
from app.schema.orm.core.submission_session import SubmissionSession

_BROWSER_SESSION_TOKEN_BYTES = 32
DEFAULT_SESSION_TTL = timedelta(days=7)


def generate_browser_session_token() -> str:
    return secrets.token_urlsafe(_BROWSER_SESSION_TOKEN_BYTES)


def hash_browser_session_token(raw_token: str) -> bytes:
    return hashlib.sha256(raw_token.encode()).digest()


def create_session(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
    survey_version_id: int,
    response_store_id: int,
    link_id: UUID | None,
    project_subject_id: UUID | None,
    raw_browser_session_token: str,
    linkage_key_version: int | None = None,
    now: datetime | None = None,
    ttl: timedelta = DEFAULT_SESSION_TTL,
) -> SubmissionSession:
    current = now or datetime.now(UTC)
    session = SubmissionSession(
        project_id=project_id,
        survey_id=survey_id,
        survey_version_id=survey_version_id,
        response_store_id=response_store_id,
        link_id=link_id,
        project_subject_id=project_subject_id,
        browser_session_token_hash=hash_browser_session_token(raw_browser_session_token),
        linkage_key_version=linkage_key_version,
        started_at=current,
        expires_at=current + ttl,
        last_activity_at=current,
    )
    db.add(session)
    flush_with_err_handle(db, contexts=[session])
    return session


def get_by_id(db: Session, session_id: UUID) -> SubmissionSession | None:
    return db.scalar(select(SubmissionSession).where(SubmissionSession.id == session_id))


def get_by_token_hash(db: Session, token_hash: bytes) -> SubmissionSession | None:
    return db.scalar(
        select(SubmissionSession).where(
            SubmissionSession.browser_session_token_hash == token_hash,
        )
    )


def lock_for_update(db: Session, session_id: UUID) -> SubmissionSession | None:
    return db.scalar(select(SubmissionSession).where(SubmissionSession.id == session_id).with_for_update())


def mark_completed(
    db: Session,
    *,
    submission_session: SubmissionSession,
    completed_at: datetime,
) -> None:
    submission_session.session_status = "completed"
    submission_session.completed_at = completed_at
    submission_session.last_activity_at = completed_at
    flush_with_err_handle(db, contexts=[submission_session])


def touch_if_active(db: Session, session_id: UUID) -> UUID | None:
    """Bump last_activity_at if the session is still in-progress and not expired.

    Returns the session_id on success, None if the session has been completed,
    expired, or abandoned.
    """
    now = datetime.now(UTC)
    result = db.execute(
        update(SubmissionSession)
        .where(
            SubmissionSession.id == session_id,
            SubmissionSession.session_status == "in_progress",
            SubmissionSession.expires_at > now,
        )
        .values(last_activity_at=now)
        .returning(SubmissionSession.id)
    )
    row = result.scalar_one_or_none()
    return row


def delete_session(db: Session, *, submission_session: SubmissionSession) -> None:
    """Delete a core session row (flush only — caller owns the commit)."""
    db.delete(submission_session)
    flush_with_err_handle(db, contexts=[submission_session])


def get_in_progress_sessions(db: Session) -> list[SubmissionSession]:
    """Return all committed in-progress sessions for reconciliation scanning."""
    return list(
        db.scalars(
            select(SubmissionSession).where(
                SubmissionSession.session_status == "in_progress",
            )
        ).all()
    )


def mark_abandoned(db: Session, *, submission_session: SubmissionSession) -> None:
    """Mark a committed core session abandoned during reconciliation or repair.

    Do not use this for pre-core-commit session-start failures; those should
    roll back instead because there is no durable session row to mark.
    """
    submission_session.session_status = "abandoned"
    flush_with_err_handle(db, contexts=[submission_session])


def list_by_survey(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
    status: SubmissionSessionStatus | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[Sequence[SubmissionSession], int]:
    """Return paginated submission sessions for a survey."""
    base = select(SubmissionSession).where(
        SubmissionSession.project_id == project_id,
        SubmissionSession.survey_id == survey_id,
    )
    if status is not None:
        base = base.where(SubmissionSession.session_status == status)

    total = db.scalar(select(func.count()).select_from(base.with_only_columns(SubmissionSession.id).subquery())) or 0

    rows = db.scalars(base.order_by(SubmissionSession.started_at.desc()).offset(offset).limit(limit)).all()

    return rows, total


def get_by_ids(
    db: Session,
    *,
    survey_id: int,
    session_ids: Sequence[UUID],
) -> Sequence[SubmissionSession]:
    """Fetch sessions by ID, filtered to the given survey."""
    if not session_ids:
        return []
    return db.scalars(
        select(SubmissionSession).where(
            SubmissionSession.survey_id == survey_id,
            SubmissionSession.id.in_(session_ids),
        )
    ).all()


def list_by_subjects(
    db: Session,
    *,
    survey_id: int,
    project_subject_ids: Sequence[UUID],
) -> Sequence[SubmissionSession]:
    """Fetch all sessions in a survey for a set of subjects."""
    if not project_subject_ids:
        return []
    return db.scalars(
        select(SubmissionSession)
        .where(
            SubmissionSession.survey_id == survey_id,
            SubmissionSession.project_subject_id.in_(project_subject_ids),
        )
        .order_by(SubmissionSession.started_at.desc())
    ).all()
