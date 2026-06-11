from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
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
    link_id: int | None,
    project_subject_id: UUID | None,
    raw_browser_session_token: str,
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
        expires_at=current + ttl,
        last_activity_at=current,
    )
    db.add(session)
    flush_with_err_handle(db, contexts=[session])
    return session
