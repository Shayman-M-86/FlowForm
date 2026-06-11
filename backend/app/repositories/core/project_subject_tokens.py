from __future__ import annotations

import hashlib
from datetime import UTC, datetime

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
