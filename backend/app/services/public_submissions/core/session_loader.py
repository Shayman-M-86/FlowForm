"""Shared current-session loader for answer save, question-viewed, and completion.

Reads the browser resume token, loads the core session and frozen survey
version, rejects forbidden edit states, derives the session locator, and
loads the response envelope id/version into the canonical session context.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.crypto.models import SubmissionSessionContext
from app.crypto.session_key import build_session_context
from app.domain.errors import (
    SessionExpiredError,
    SessionInvalidError,
    SessionNotFoundError,
)
from app.repositories.core import submission_sessions as ssr
from app.schema.orm.core.submission_session import SubmissionSession

if TYPE_CHECKING:
    from app.cache import AppCache
    from app.crypto._internal.client_extension import CryptoClients

_FORBIDDEN_EDIT_STATUSES = frozenset({"abandoned"})


def load_current_session(
    db: Session,
    response_db: Session,
    raw_resume_token: str,
    *,
    allow_completed: bool = False,
    cache: AppCache,
    clients: CryptoClients,
) -> SubmissionSessionContext:
    """Load and validate the current session from a browser resume token.

    The raw token is hashed before lookup. A matching, unexpired
    SubmissionSessionContext is returned from the write-context cache when
    possible; otherwise the core session row is loaded, validated, and expanded
    into the canonical context by resolving its response-envelope locator and
    crypto material.

    Side effects are limited to cache activity: this may read/write/evict the
    session write-context cache and may populate crypto caches indirectly while
    building the context. It does not flush, commit, touch last_activity_at, or
    change the session status.

    Raises domain errors for forbidden edit states: missing, expired,
    abandoned, and completed unless allow_completed is true. Cached contexts
    are checked for token mismatch and expiry, but do not re-read session
    status from the database until the cache entry is missed or evicted.
    """
    token_hash = ssr.hash_browser_session_token(raw_resume_token)

    cached = _load_cached_context(token_hash, cache)
    if cached is not None:
        return cached

    session = _get_submission_session_orm(db, token_hash, allow_completed=allow_completed)

    ctx = build_session_context(
        db, response_db, session=session, cache=cache, clients=clients,
    )

    cache.sessions.write_context.put(token_hash, ctx)

    return ctx


def _load_cached_context(
    token_hash: bytes,
    cache: AppCache,
) -> SubmissionSessionContext | None:
    session_cache = cache.sessions.write_context
    cached = session_cache.get(token_hash)
    if cached is None:
        return None

    if cached.browser_session_token_hash != token_hash:
        session_cache.evict(token_hash)
        raise SessionNotFoundError()

    if _is_expired(cached.expires_at):
        session_cache.evict(token_hash)
        raise SessionExpiredError()

    return cached


def _is_expired(expires_at: datetime) -> bool:
    normalized = expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at
    return datetime.now(UTC) > normalized


def _get_submission_session_orm(
    db: Session,
    token_hash: bytes,
    allow_completed: bool = False,
) -> SubmissionSession:
    """Get the SubmissionSession ORM object by token hash."""
    session = ssr.get_by_token_hash(db, token_hash)
    if session is None:
        raise SessionNotFoundError()

    if _is_expired(session.expires_at):
        raise SessionExpiredError()

    if session.session_status in _FORBIDDEN_EDIT_STATUSES:
        raise SessionInvalidError(f"Session is {session.session_status}.")

    if session.session_status == "completed" and not allow_completed:
        raise SessionInvalidError("Session is already completed.")
    return session
