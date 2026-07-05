"""Unit tests for session key create/load functions."""

from __future__ import annotations

import os
import uuid

from app.cache import AppCache, create_app_cache
from app.crypto.models import (
    PlaintextSurveyKey,
    SessionDEKContext,
    SessionLocator,
)
from app.crypto.session_key import create_session_key

_SURVEY_KEY = PlaintextSurveyKey(os.urandom(32))


def _dek_context() -> SessionDEKContext:
    return SessionDEKContext(
        session_id=uuid.uuid4(),
        crypto_version=1,
        project_id=1,
        survey_id=1,
        session_locator=SessionLocator(os.urandom(32)),
    )


def _app_cache() -> AppCache:
    return create_app_cache()


class TestCreateSessionKey:
    def test_returns_plaintext_and_wrapped(self) -> None:
        ctx = _dek_context()
        cache = _app_cache()
        result = create_session_key(ctx, _SURVEY_KEY, cache=cache)

        assert len(result.plaintext_key) == 32
        assert len(result.wrapped_key) > 0
        assert result.plaintext_key != result.wrapped_key

    def test_caches_plaintext_key(self) -> None:
        ctx = _dek_context()
        cache = _app_cache()
        result = create_session_key(ctx, _SURVEY_KEY, cache=cache)

        cached = cache.crypto.session_deks.get(ctx.session_id)
        assert cached == result.plaintext_key

    def test_wrapped_key_can_be_unwrapped(self) -> None:
        from app.crypto._internal.aad import build_session_dek_wrap_aad
        from app.crypto._internal.wrapping import unwrap_session_key

        ctx = _dek_context()
        cache = _app_cache()
        result = create_session_key(ctx, _SURVEY_KEY, cache=cache)

        aad = build_session_dek_wrap_aad(ctx)
        unwrapped = unwrap_session_key(
            wrapped_key=result.wrapped_key,
            survey_key=_SURVEY_KEY,
            aad=aad,
        )
        assert unwrapped == result.plaintext_key
