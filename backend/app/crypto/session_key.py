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
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.crypto._internal.aad import build_session_dek_wrap_aad
from app.crypto._internal.errors import SessionDEKUnavailableError
from app.crypto._internal.models import SESSION_DEK_BYTES
from app.crypto._internal.wrapping import unwrap_session_key, wrap_session_key
from app.crypto.locators import resolve_existing_session_locator
from app.crypto.models import (
    NewSessionKey,
    PlaintextSessionKey,
    PlaintextSurveyKey,
    SessionDEKContext,
    SessionKeyResolver,
    SessionLocator,
    SubmissionSessionContext,
    WrappedSessionKey,
)
from app.crypto.survey_key import start_plaintext_survey_key_load
from app.domain.errors import EnvelopeNotFoundError
from app.repositories.response import response_envelope_repo
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.response.response_envelope import ResponseEnvelope

if TYPE_CHECKING:
    from app.cache import AppCache
    from app.crypto._internal.client_extension import CryptoClients

logger = logging.getLogger(__name__)


def build_session_context(
    db: Session,
    response_db: Session,
    *,
    session: SubmissionSession,
    cache: AppCache,
    clients: CryptoClients,
) -> SubmissionSessionContext:
    """Build the unified session context from a SubmissionSession ORM row.

    Resolves the session locator and response envelope. If the plaintext
    DEK is already cached it is stored directly; otherwise a lazy resolver
    is attached that will unwrap the DEK on first property access and
    mutate the frozen field in-place (so the cached reference is updated
    transparently).
    """
    session_locator, linkage_key = resolve_existing_session_locator(
        db,
        session.id,
        session.linkage_key_version,
        cache=cache,
        clients=clients,
    )

    envelope = response_envelope_repo.get_by_locator(response_db, session_locator)
    if envelope is None:
        raise EnvelopeNotFoundError()

    crypto_cache = cache.crypto
    cached_dek = crypto_cache.session_deks.get(session.id)

    if cached_dek is not None:
        dek_or_resolver: PlaintextSessionKey | SessionKeyResolver = cached_dek
    else:
        dek_context = SessionDEKContext(
            session_id=session.id,
            crypto_version=envelope.crypto_version,
            project_id=session.project_id,
            survey_id=session.survey_id,
            session_locator=session_locator,
        )
        aad = build_session_dek_wrap_aad(dek_context)
        survey_key_loader = start_plaintext_survey_key_load(
            db,
            project_id=session.project_id,
            survey_id=session.survey_id,
            cache=cache,
            clients=clients,
        )

        def resolve() -> PlaintextSessionKey:
            cached_late = crypto_cache.session_deks.get(session.id)
            if cached_late is not None:
                return cached_late

            try:
                plaintext_key = unwrap_session_key(
                    wrapped_key=WrappedSessionKey(envelope.wrapped_session_dek),
                    survey_key=survey_key_loader(),
                    aad=aad,
                )
            except Exception as exc:
                logger.error("session_key unwrap_failed session_id=%s", session.id)
                raise SessionDEKUnavailableError() from exc

            crypto_cache.session_deks.put(session.id, plaintext_key)
            return plaintext_key

        dek_or_resolver = resolve

    return SubmissionSessionContext(
        session_id=session.id,
        project_id=session.project_id,
        survey_id=session.survey_id,
        survey_version_id=session.survey_version_id,
        envelope_id=envelope.id,
        session_locator=session_locator,
        linkage_key=linkage_key,
        linkage_key_version=linkage_key.version,
        _session_dek=dek_or_resolver,
        crypto_version=envelope.crypto_version,
        expires_at=session.expires_at,
        browser_session_token_hash=session.browser_session_token_hash,
    )


def create_session_key(
    context: SessionDEKContext,
    survey_key: PlaintextSurveyKey,
    *,
    cache: AppCache,
) -> NewSessionKey:
    """Generate a new session key and wrap it under the survey key.

    Returns both plaintext and wrapped forms. Side effects: cache write.
    """
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

    cache.crypto.session_deks.put(context.session_id, plaintext_key)
    return new_key


def clear_plaintext_session_key(session_id: UUID, *, cache: AppCache) -> None:
    """Evict a cached plaintext session key for a session."""
    cache.crypto.session_deks.evict(session_id)


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
    cache: AppCache,
    clients: CryptoClients,
) -> SessionEnvelopeCryptoContext:
    """Load the response envelope and plaintext session key for a session."""
    ctx = build_session_context(
        db, response_db, session=session, cache=cache, clients=clients,
    )

    envelope = response_db.get(ResponseEnvelope, ctx.envelope_id)
    if envelope is None:
        raise EnvelopeNotFoundError()

    return SessionEnvelopeCryptoContext(
        session_locator=ctx.session_locator,
        envelope=envelope,
        plaintext_key=ctx.plaintext_session_dek,
    )
