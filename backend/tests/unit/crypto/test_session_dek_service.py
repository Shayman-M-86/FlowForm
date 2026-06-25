"""Unit tests for session key create/load functions."""

from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

from app.cache import LockedTTLCache
from app.crypto.models import (
    PlaintextSurveyKey,
    SessionDEKContext,
    SessionLocator,
)
from app.crypto.session_key import create_session_key

_SESSION_KEY_MODULE = "app.crypto.session_key"
_SURVEY_KEY = PlaintextSurveyKey(os.urandom(32))


def _dek_context() -> SessionDEKContext:
    return SessionDEKContext(
        session_id=uuid.uuid4(),
        crypto_version=1,
        project_id=1,
        survey_id=1,
        session_locator=SessionLocator(os.urandom(32)),
    )


def _mock_cache():
    cache = MagicMock()
    cache.session_deks = LockedTTLCache(name="test_deks", maxsize=16, ttl_seconds=60)
    return cache


class TestCreateSessionKey:
    def test_returns_plaintext_and_wrapped(self) -> None:
        ctx = _dek_context()
        mock_cache = _mock_cache()
        with patch(f"{_SESSION_KEY_MODULE}.get_app_cache") as get_cache:
            get_cache.return_value.crypto = mock_cache
            result = create_session_key(ctx, _SURVEY_KEY)

        assert len(result.plaintext_key) == 32
        assert len(result.wrapped_key) > 0
        assert result.plaintext_key != result.wrapped_key

    def test_caches_plaintext_key(self) -> None:
        ctx = _dek_context()
        mock_cache = _mock_cache()
        with patch(f"{_SESSION_KEY_MODULE}.get_app_cache") as get_cache:
            get_cache.return_value.crypto = mock_cache
            result = create_session_key(ctx, _SURVEY_KEY)

        cached = mock_cache.session_deks.get(ctx.session_id)
        assert cached == result.plaintext_key

    def test_wrapped_key_can_be_unwrapped(self) -> None:
        from app.crypto._internal.aad import build_session_dek_wrap_aad
        from app.crypto._internal.wrapping import unwrap_session_key

        ctx = _dek_context()
        mock_cache = _mock_cache()
        with patch(f"{_SESSION_KEY_MODULE}.get_app_cache") as get_cache:
            get_cache.return_value.crypto = mock_cache
            result = create_session_key(ctx, _SURVEY_KEY)

        aad = build_session_dek_wrap_aad(ctx)
        unwrapped = unwrap_session_key(
            wrapped_key=result.wrapped_key,
            survey_key=_SURVEY_KEY,
            aad=aad,
        )
        assert unwrapped == result.plaintext_key
