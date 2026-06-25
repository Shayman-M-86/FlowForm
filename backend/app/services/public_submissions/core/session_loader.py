"""Shared current-session loader for answer save, question-viewed, and completion.

Reads the browser resume token, loads the core session and frozen survey
version, rejects forbidden edit states, derives the session locator, and
loads the response envelope id/version into the canonical session context.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.extensions import app_cache
from app.crypto.locators import resolve_existing_session_locator
from app.crypto.models import SessionContext
from app.domain.errors import (
    EnvelopeNotFoundError,
    SessionExpiredError,
    SessionInvalidError,
    SessionNotFoundError,
)
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_envelope_repo

_FORBIDDEN_EDIT_STATUSES = frozenset({"abandoned"})


def load_current_session(
    db: Session,
    response_db: Session,
    raw_resume_token: str,
    *,
    allow_completed: bool = False,
) -> SessionContext:
    """Load and validate the current session from a browser resume token.

    Raises domain errors for every forbidden edit state:
    missing, expired, abandoned, and completed (unless allow_completed).
    """
    token_hash = ssr.hash_browser_session_token(raw_resume_token)

    cached = _load_cached_context(token_hash)
    if cached is not None:
        return cached

    session = ssr.get_by_token_hash(db, token_hash)
    if session is None:
        raise SessionNotFoundError()

    if _is_expired(session.expires_at):
        raise SessionExpiredError()

    if session.session_status in _FORBIDDEN_EDIT_STATUSES:
        raise SessionInvalidError(f"Session is {session.session_status}.")

    if session.session_status == "completed" and not allow_completed:
        raise SessionInvalidError("Session is already completed.")

    session_locator, linkage_key = resolve_existing_session_locator(
        db,
        session.id,
        session.linkage_key_version,
    )

    envelope = response_envelope_repo.get_by_locator(response_db, session_locator)
    if envelope is None:
        raise EnvelopeNotFoundError()

    return SessionContext(
        session_ref=session.to_crypto_ref(),
        session_locator=session_locator,
        envelope_id=envelope.id,
        linkage_key=linkage_key,
        crypto_version=envelope.crypto_version,
    )


def _load_cached_context(
    token_hash: bytes,
) -> SessionContext | None:
    cache = app_cache.sessions.write_context
    cached = cache.get(token_hash)
    if cached is None:
        return None

    if cached.browser_session_token_hash != token_hash:
        cache.evict(token_hash)
        raise SessionNotFoundError()

    if _is_expired(cached.expires_at):
        cache.evict(token_hash)
        raise SessionExpiredError()

    return replace(cached, loaded_from_cache=True)


def _is_expired(expires_at: datetime) -> bool:
    normalized = expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at
    return datetime.now(UTC) > normalized
