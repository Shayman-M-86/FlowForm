"""Session key lifecycle: create, load, and clear.

Tier 2 of the key hierarchy. Each session has its own key,
wrapped under the survey key with AES-256-GCM. Plaintext keys are cached
to avoid repeated unwraps. Callers describe the session via
SessionDEKContext; this module derives the wrap AAD itself.
See _internal/KEY_HIERARCHY.md.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.cache import get_app_cache
from app.crypto._internal.aad import build_session_dek_wrap_aad
from app.crypto._internal.errors import SessionDEKUnavailableError
from app.crypto._internal.models import SESSION_DEK_BYTES
from app.crypto._internal.wrapping import unwrap_session_key, wrap_session_key
from app.crypto.locators import resolve_existing_session_locator
from app.crypto.models import (
    NewSessionKey,
    PlaintextSessionKey,
    PlaintextSurveyKey,
    SessionKeyResolver,
    SessionContext,
    SessionDEKContext,
    SessionLocator,
    WrappedSessionKey,
)
from app.crypto.survey_key import start_plaintext_survey_key_load
from app.domain.errors import EnvelopeNotFoundError
from app.repositories.response import response_envelope_repo
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.response.response_envelope import ResponseEnvelope

logger = logging.getLogger(__name__)


def create_session_key(
    context: SessionDEKContext,
    survey_key: PlaintextSurveyKey,
) -> NewSessionKey:
    """Generate a new session key and wrap it under the survey key.

    Returns both plaintext and wrapped forms. Side effects: cache write.
    """
    cache = get_app_cache().crypto
    aad = build_session_dek_wrap_aad(context)
    plaintext_key = PlaintextSessionKey(os.urandom(SESSION_DEK_BYTES))

    try:
        wrapped = wrap_session_key(
            plaintext_key=plaintext_key,
            survey_key=survey_key,
            aad=aad,
        )

        new_key = NewSessionKey(
            plaintext_key=plaintext_key,
            wrapped_key=wrapped,
        )
    except Exception as exc:
        logger.error("session_key wrap_failed session_id=%s", context.session_id)
        raise SessionDEKUnavailableError() from exc

    cache.session_deks.put(context.session_id, plaintext_key)
    return new_key


def load_plaintext_session_key(
    db: Session,
    response_db: Session,
    *,
    context: SessionContext,
) -> PlaintextSessionKey:
    """Return the plaintext session key, resolving stored material on cache miss.

    Checks the session-DEK cache first. On a miss, fetches the response
    envelope by locator, loads the plaintext survey key, unwraps the stored
    session key, and caches the plaintext result.
    """
    return start_plaintext_session_key_load(db, response_db, context=context)()


def start_plaintext_session_key_load(
    db: Session,
    response_db: Session,
    *,
    context: SessionContext,
) -> SessionKeyResolver:
    """Start resolving a plaintext session key and return a blocking resolver.

    On a session-key cache hit, the resolver returns immediately. On a miss,
    this fetches the response envelope now and starts the threaded survey-key
    load so KMS unwrap can overlap with later answer-write work.
    """
    cache = get_app_cache().crypto

    cached = cache.session_deks.get(context.session_id)
    if cached is not None:
        return lambda: cached

    envelope = _get_response_envelope(response_db, context)
    aad = build_session_dek_wrap_aad(context.session_dek_context)
    survey_key_loader = start_plaintext_survey_key_load(
        db,
        project_id=context.project_id,
        survey_id=context.survey_id,
    )

    def resolve() -> PlaintextSessionKey:
        cached_late = cache.session_deks.get(context.session_id)
        if cached_late is not None:
            return cached_late

        try:
            plaintext_key = unwrap_session_key(
                wrapped_key=WrappedSessionKey(envelope.wrapped_session_dek),
                survey_key=survey_key_loader(),
                aad=aad,
            )
        except Exception as exc:
            logger.error("session_key unwrap_failed session_id=%s", context.session_id)
            raise SessionDEKUnavailableError() from exc

        cache.session_deks.put(context.session_id, plaintext_key)
        return plaintext_key

    return resolve


def clear_plaintext_session_key(session_id: UUID) -> None:
    """Evict a cached plaintext session key for a session."""
    get_app_cache().crypto.session_deks.evict(session_id)


def _get_response_envelope(
    response_db: Session,
    context: SessionContext,
) -> ResponseEnvelope:
    """Fetch the response envelope that stores the wrapped session key."""
    envelope = response_db.get(ResponseEnvelope, context.envelope_id)
    if envelope is None:
        raise EnvelopeNotFoundError()
    return envelope


@dataclass(frozen=True, slots=True)
class SessionEnvelopeCryptoContext:
    """Crypto material needed to work with one response envelope."""

    session_locator: SessionLocator
    envelope: ResponseEnvelope
    plaintext_key: PlaintextSessionKey


def load_session_envelope_crypto_context(
    db: Session,
    response_db: Session,
    *,
    session: SubmissionSession,
) -> SessionEnvelopeCryptoContext:
    """Load the response envelope and plaintext session key for a session."""
    session_locator, linkage_key = resolve_existing_session_locator(
        db,
        session.id,
        session.linkage_key_version,
    )

    envelope = response_envelope_repo.get_by_locator(response_db, session_locator)
    if envelope is None:
        raise EnvelopeNotFoundError()

    context = SessionContext(
        session_ref=session.to_crypto_ref(),
        session_locator=session_locator,
        envelope_id=envelope.id,
        linkage_key=linkage_key,
        crypto_version=envelope.crypto_version,
    )
    plaintext_key = load_plaintext_session_key(
        db,
        response_db,
        context=context,
    )

    return SessionEnvelopeCryptoContext(
        session_locator=session_locator,
        envelope=envelope,
        plaintext_key=plaintext_key,
    )
