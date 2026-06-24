"""Unit tests for SessionDEKService."""

from __future__ import annotations

import uuid
from collections.abc import Hashable
from datetime import UTC, datetime, timedelta

import pytest

from app.crypto.cache import LockedTTLCache
from app.crypto.errors import SessionDEKUnavailableError
from app.crypto.services.session_dek_service import NewSessionDEK, SessionDEKService


def _make_service() -> SessionDEKService:
    cache: LockedTTLCache[bytes] = LockedTTLCache(
        name="test_session_dek", maxsize=100, ttl_seconds=3600,
    )
    return SessionDEKService(cache=cache)


_S1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
_S2 = uuid.UUID("00000000-0000-0000-0000-000000000002")
_SURVEY_BRANCH_KEY = b"\xcc" * 32
_WRAP_AAD = b"test-aad"
_EXPIRES = datetime.now(UTC) + timedelta(hours=1)


def _create_wrapped_dek(
    svc: SessionDEKService,
    session_id: uuid.UUID = _S1,
) -> NewSessionDEK:
    """Helper: create a real wrapped DEK so unwrap tests have valid material."""
    return svc.create_for_session(
        session_id,
        _SURVEY_BRANCH_KEY,
        _EXPIRES,
        wrap_aad=_WRAP_AAD,
    )


def _branch_key_loader() -> bytes:
    return _SURVEY_BRANCH_KEY


class TestGetForSession:
    def test_returns_plaintext_dek(self) -> None:
        svc = _make_service()
        created = _create_wrapped_dek(svc, _S1)
        svc.clear_for_session(_S1)

        dek = svc.get_for_session(
            _S1,
            created.wrapped_session_dek,
            _EXPIRES,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=_branch_key_loader,
        )
        assert dek == created.plaintext_dek

    def test_caches_on_second_call(self) -> None:
        svc = _make_service()
        created = _create_wrapped_dek(svc, _S1)
        svc.clear_for_session(_S1)

        loader_calls = 0

        def counting_loader() -> bytes:
            nonlocal loader_calls
            loader_calls += 1
            return _SURVEY_BRANCH_KEY

        svc.get_for_session(
            _S1,
            created.wrapped_session_dek,
            _EXPIRES,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=counting_loader,
        )
        dek = svc.get_for_session(
            _S1,
            created.wrapped_session_dek,
            _EXPIRES,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=counting_loader,
        )
        assert loader_calls == 1
        assert dek == created.plaintext_dek

    def test_different_sessions_cached_separately(self) -> None:
        svc = _make_service()
        created_a = _create_wrapped_dek(svc, _S1)
        created_b = _create_wrapped_dek(svc, _S2)
        svc.clear_for_session(_S1)
        svc.clear_for_session(_S2)

        loader_calls = 0

        def counting_loader() -> bytes:
            nonlocal loader_calls
            loader_calls += 1
            return _SURVEY_BRANCH_KEY

        a = svc.get_for_session(
            _S1,
            created_a.wrapped_session_dek,
            _EXPIRES,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=counting_loader,
        )
        b = svc.get_for_session(
            _S2,
            created_b.wrapped_session_dek,
            _EXPIRES,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=counting_loader,
        )
        assert loader_calls == 2
        assert a == created_a.plaintext_dek
        assert b == created_b.plaintext_dek
        assert a != b

    def test_expired_cache_triggers_unwrap(self) -> None:
        from cachetools import TTLCache

        fake_time = 0.0

        def tick() -> float:
            return fake_time

        ttl_cache: TTLCache[Hashable, bytes] = TTLCache(maxsize=100, ttl=1, timer=tick)
        cache: LockedTTLCache[bytes] = LockedTTLCache(
            name="test_expiry", maxsize=100, ttl_seconds=1,
        )
        cache._cache = ttl_cache
        svc = SessionDEKService(cache=cache)

        created = svc.create_for_session(
            _S1, _SURVEY_BRANCH_KEY, _EXPIRES, wrap_aad=_WRAP_AAD,
        )

        fake_time = 2.0

        loader_calls = 0

        def counting_loader() -> bytes:
            nonlocal loader_calls
            loader_calls += 1
            return _SURVEY_BRANCH_KEY

        svc.get_for_session(
            _S1,
            created.wrapped_session_dek,
            _EXPIRES,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=counting_loader,
        )
        assert loader_calls == 1

    def test_unwrap_failure_raises_app_error(self) -> None:
        svc = _make_service()
        bad_wrapped = b"\x00" * 64

        with pytest.raises(SessionDEKUnavailableError):
            svc.get_for_session(
                _S1,
                bad_wrapped,
                _EXPIRES,
                wrap_aad=_WRAP_AAD,
                survey_branch_key_loader=_branch_key_loader,
            )

    def test_session_expiry_does_not_override_cache_ttl(self) -> None:
        svc = _make_service()
        past = datetime.now(UTC) - timedelta(seconds=10)
        created = _create_wrapped_dek(svc, _S1)
        svc.clear_for_session(_S1)

        loader_calls = 0

        def counting_loader() -> bytes:
            nonlocal loader_calls
            loader_calls += 1
            return _SURVEY_BRANCH_KEY

        svc.get_for_session(
            _S1,
            created.wrapped_session_dek,
            past,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=counting_loader,
        )
        svc.get_for_session(
            _S1,
            created.wrapped_session_dek,
            past,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=counting_loader,
        )
        assert loader_calls == 1


class TestClearForSession:
    def test_clears_cached_session(self) -> None:
        svc = _make_service()
        created = _create_wrapped_dek(svc, _S1)

        svc.clear_for_session(_S1)

        loader_calls = 0

        def counting_loader() -> bytes:
            nonlocal loader_calls
            loader_calls += 1
            return _SURVEY_BRANCH_KEY

        svc.get_for_session(
            _S1,
            created.wrapped_session_dek,
            _EXPIRES,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=counting_loader,
        )
        assert loader_calls == 1

    def test_clear_missing_is_noop(self) -> None:
        svc = _make_service()
        svc.clear_for_session(_S1)


class TestTTLExpiry:
    def test_expired_entry_triggers_unwrap(self) -> None:
        """Cache with a 1-second TTL expires entries automatically."""
        from cachetools import TTLCache

        fake_time = 0.0

        def tick() -> float:
            return fake_time

        ttl_cache: TTLCache[Hashable, bytes] = TTLCache(maxsize=100, ttl=1, timer=tick)
        cache: LockedTTLCache[bytes] = LockedTTLCache(
            name="test_short_ttl", maxsize=100, ttl_seconds=1,
        )
        cache._cache = ttl_cache
        svc = SessionDEKService(cache=cache)

        created = svc.create_for_session(
            _S1, _SURVEY_BRANCH_KEY, _EXPIRES, wrap_aad=_WRAP_AAD,
        )

        fake_time = 2.0

        loader_calls = 0

        def counting_loader() -> bytes:
            nonlocal loader_calls
            loader_calls += 1
            return _SURVEY_BRANCH_KEY

        svc.get_for_session(
            _S1,
            created.wrapped_session_dek,
            _EXPIRES,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=counting_loader,
        )
        assert loader_calls == 1


class TestCreateForSession:
    def test_returns_plaintext_and_wrapped(self) -> None:
        svc = _make_service()
        result = _create_wrapped_dek(svc, _S1)
        assert isinstance(result, NewSessionDEK)
        assert len(result.plaintext_dek) == 32
        assert len(result.wrapped_session_dek) > 0

    def test_caches_plaintext_dek(self) -> None:
        svc = _make_service()
        created = _create_wrapped_dek(svc, _S1)

        loader_calls = 0

        def counting_loader() -> bytes:
            nonlocal loader_calls
            loader_calls += 1
            return _SURVEY_BRANCH_KEY

        dek = svc.get_for_session(
            _S1,
            created.wrapped_session_dek,
            _EXPIRES,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=counting_loader,
        )
        assert loader_calls == 0
        assert dek == created.plaintext_dek

    def test_wrap_failure_raises_app_error(self) -> None:
        svc = _make_service()
        bad_key = b"\x00" * 16  # wrong length

        with pytest.raises((SessionDEKUnavailableError, ValueError)):
            svc.create_for_session(
                _S1, bad_key, _EXPIRES, wrap_aad=_WRAP_AAD,
            )

    def test_create_caches_plaintext_dek_even_if_session_expiry_is_past(self) -> None:
        svc = _make_service()
        past = datetime.now(UTC) - timedelta(seconds=10)
        result = svc.create_for_session(
            _S1, _SURVEY_BRANCH_KEY, past, wrap_aad=_WRAP_AAD,
        )
        assert len(result.plaintext_dek) == 32

        loader_calls = 0

        def counting_loader() -> bytes:
            nonlocal loader_calls
            loader_calls += 1
            return _SURVEY_BRANCH_KEY

        svc.get_for_session(
            _S1,
            result.wrapped_session_dek,
            _EXPIRES,
            wrap_aad=_WRAP_AAD,
            survey_branch_key_loader=counting_loader,
        )
        assert loader_calls == 0
