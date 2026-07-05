"""Contract tests for session key wrapping and cache behaviour."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from cryptography.exceptions import InvalidTag

from app.cache import AppCache, create_app_cache
from app.crypto._internal.aad import build_session_dek_wrap_aad
from app.crypto._internal.wrapping import unwrap_session_key
from app.crypto.models import (
    PlaintextSurveyKey,
    SessionDEKContext,
    SessionLocator,
)
from app.crypto.session_key import clear_plaintext_session_key, create_session_key


def _survey_key(value: bytes | None = None) -> PlaintextSurveyKey:
    return PlaintextSurveyKey(value or os.urandom(32))


def _session_context(session_id: UUID | None = None) -> SessionDEKContext:
    return SessionDEKContext(
        session_id=session_id or uuid4(),
        crypto_version=1,
        project_id=11,
        survey_id=22,
        session_locator=SessionLocator(os.urandom(32)),
    )


def _cache() -> AppCache:
    return create_app_cache()


def test_create_session_key_returns_plaintext_and_wrapped_forms() -> None:
    """Creating a session key should return usable plaintext and wrapped key material."""
    result = create_session_key(_session_context(), _survey_key(), cache=_cache())

    assert len(result.plaintext_key) == 32
    assert len(result.wrapped_key) > 12
    assert result.plaintext_key != result.wrapped_key


def test_create_session_key_caches_plaintext_key_by_session_id() -> None:
    """The plaintext session key should be cached under the core session ID."""
    ctx = _session_context()
    cache = _cache()

    result = create_session_key(ctx, _survey_key(), cache=cache)

    assert cache.crypto.session_deks.get(ctx.session_id) == result.plaintext_key


def test_wrapped_session_key_unwraps_with_same_survey_key_and_context() -> None:
    """Wrapped session keys should unwrap with the same survey key and AAD context."""
    ctx = _session_context()
    survey_key = _survey_key()
    result = create_session_key(ctx, survey_key, cache=_cache())

    unwrapped = unwrap_session_key(
        wrapped_key=result.wrapped_key,
        survey_key=survey_key,
        aad=build_session_dek_wrap_aad(ctx),
    )

    assert unwrapped == result.plaintext_key


def test_wrapped_session_key_rejects_wrong_survey_key() -> None:
    """A session key wrapped for one survey key should not unwrap under another."""
    ctx = _session_context()
    result = create_session_key(ctx, _survey_key(b"a" * 32), cache=_cache())

    with pytest.raises(InvalidTag):
        unwrap_session_key(
            wrapped_key=result.wrapped_key,
            survey_key=_survey_key(b"b" * 32),
            aad=build_session_dek_wrap_aad(ctx),
        )


def test_wrapped_session_key_rejects_wrong_context() -> None:
    """Session-DEK wrap AAD should bind the key to its session context."""
    ctx = _session_context()
    result = create_session_key(ctx, _survey_key(b"a" * 32), cache=_cache())
    wrong_ctx = SessionDEKContext(
        session_id=ctx.session_id,
        crypto_version=ctx.crypto_version,
        project_id=ctx.project_id,
        survey_id=ctx.survey_id + 1,
        session_locator=ctx.session_locator,
    )

    with pytest.raises(InvalidTag):
        unwrap_session_key(
            wrapped_key=result.wrapped_key,
            survey_key=_survey_key(b"a" * 32),
            aad=build_session_dek_wrap_aad(wrong_ctx),
        )


def test_clear_plaintext_session_key_evicts_cached_key() -> None:
    """Clearing a session key should remove the plaintext key from cache."""
    ctx = _session_context()
    cache = _cache()
    create_session_key(ctx, _survey_key(), cache=cache)

    clear_plaintext_session_key(ctx.session_id, cache=cache)

    assert cache.crypto.session_deks.get(ctx.session_id) is None
