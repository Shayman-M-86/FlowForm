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
import uuid

from sqlalchemy.orm import Session

from app.cache import get_app_cache
from app.crypto._internal.aad import build_session_dek_wrap_aad
from app.crypto._internal.errors import SessionDEKUnavailableError
from app.crypto._internal.models import SESSION_DEK_BYTES
from app.crypto._internal.wrapping import unwrap_session_key, wrap_session_key
from app.crypto.models import (
    NewSessionKey,
    PlaintextSessionKey,
    PlaintextSurveyKey,
    SessionDEKContext,
    WrappedSessionKey,
)
from app.crypto.survey_key import load_plaintext_survey_key
from app.domain.errors import EnvelopeNotFoundError
from app.repositories.response import response_envelope_repo
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
    session_id: uuid.UUID,
    project_id: int,
    survey_id: int,
    session_locator: bytes,
) -> PlaintextSessionKey:
    """Return the plaintext session key, resolving stored material on cache miss.

    Checks the session-DEK cache first. On a miss, fetches the response
    envelope by locator, loads the plaintext survey key, unwraps the stored
    session key, and caches the plaintext result.
    """
    cache = get_app_cache().crypto

    cached = cache.session_deks.get(session_id)
    if cached is not None:
        return cached

    envelope = _get_response_envelope(response_db, session_locator)
    context = SessionDEKContext(
        session_id=session_id,
        crypto_version=envelope.crypto_version,
        project_id=project_id,
        survey_id=survey_id,
        session_locator=session_locator,
    )
    aad = build_session_dek_wrap_aad(context)
    survey_key = load_plaintext_survey_key(
        db,
        project_id=project_id,
        survey_id=survey_id,
    )

    try:
        plaintext_key = unwrap_session_key(
            wrapped_key=WrappedSessionKey(envelope.wrapped_session_dek),
            survey_key=survey_key,
            aad=aad,
        )
    except Exception as exc:
        logger.error("session_key unwrap_failed session_id=%s", session_id)
        raise SessionDEKUnavailableError() from exc

    cache.session_deks.put(session_id, plaintext_key)
    return plaintext_key


def clear_plaintext_session_key(session_id: uuid.UUID) -> None:
    """Evict a cached plaintext session key for a session."""
    get_app_cache().crypto.session_deks.evict(session_id)


def _get_response_envelope(
    response_db: Session,
    session_locator: bytes,
) -> ResponseEnvelope:
    """Fetch the response envelope that stores the wrapped session key."""
    envelope = response_envelope_repo.get_by_locator(response_db, session_locator)
    if envelope is None:
        raise EnvelopeNotFoundError()
    return envelope
