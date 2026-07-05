from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.project_subject import ProjectSubjectToken


def hash_recognition_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def get_active_token(
    db: Session,
    *,
    project_id: int,
    raw_token: str,
    now: datetime | None = None,
) -> ProjectSubjectToken | None:
    current = now or datetime.now(UTC)
    return db.scalar(
        select(ProjectSubjectToken).where(
            ProjectSubjectToken.project_id == project_id,
            ProjectSubjectToken.token_hash == hash_recognition_token(raw_token),
            ProjectSubjectToken.revoked_at.is_(None),
            ProjectSubjectToken.expires_at > current,
        )
    )


def mark_used(db: Session, *, token: ProjectSubjectToken, now: datetime | None = None) -> ProjectSubjectToken:
    token.last_used_at = now or datetime.now(UTC)
    flush_with_err_handle(db, contexts=[token])
    return token


_TOKEN_BYTES = 32
_TOKEN_LIFETIME_DAYS = 365


def create_token(
    db: Session,
    *,
    project_id: int,
    project_subject_id: UUID,
    now: datetime | None = None,
) -> tuple[ProjectSubjectToken, str]:
    """Create a new recognition token. Returns (ORM row, raw token). Raw token is never stored."""
    current = now or datetime.now(UTC)
    raw_token = secrets.token_urlsafe(_TOKEN_BYTES)
    token = ProjectSubjectToken(
        project_id=project_id,
        project_subject_id=project_subject_id,
        token_hash=hash_recognition_token(raw_token),
        expires_at=current + timedelta(days=_TOKEN_LIFETIME_DAYS),
    )
    db.add(token)
    flush_with_err_handle(db, contexts=[token])
    return token, raw_token


def revoke_token(
    db: Session, *, token: ProjectSubjectToken, now: datetime | None = None
) -> ProjectSubjectToken:
    """Revoke a token so it is no longer valid for recognition."""
    token.revoked_at = now or datetime.now(UTC)
    flush_with_err_handle(db, contexts=[token])
    return token


def get_active_token_for_subject(
    db: Session,
    *,
    project_id: int,
    project_subject_id: UUID,
    now: datetime | None = None,
) -> ProjectSubjectToken | None:
    """Find a valid (not expired, not revoked) token for a given subject."""
    current = now or datetime.now(UTC)
    return db.scalar(
        select(ProjectSubjectToken).where(
            ProjectSubjectToken.project_id == project_id,
            ProjectSubjectToken.project_subject_id == project_subject_id,
            ProjectSubjectToken.revoked_at.is_(None),
            ProjectSubjectToken.expires_at > current,
        )
    )
