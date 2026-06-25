"""Unit tests for worker-local crypto key caches."""

from __future__ import annotations

import uuid
from collections.abc import Hashable
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from cachetools import TTLCache
from flask import Flask

from app.cache import LockedTTLCache, create_app_cache
from app.cache._registry import EXTENSION_KEY
from app.cache.sessions import SessionWriteContext
from app.crypto.operations.models import LinkageKey


def _make_cache(ttl_seconds: int = 3600) -> LockedTTLCache[bytes]:
    return LockedTTLCache(name="test_key", maxsize=100, ttl_seconds=ttl_seconds)


class TestLockedTTLCacheBasic:
    def test_put_and_get(self) -> None:
        cache = _make_cache()
        key = b"\x01" * 32
        value = b"\xaa" * 32
        cache.put(key, value)
        assert cache.get(key) == value

    def test_get_missing_returns_none(self) -> None:
        cache = _make_cache()
        assert cache.get(b"\x01" * 32) is None

    def test_evict_removes_entry(self) -> None:
        cache = _make_cache()
        key = b"\x01" * 32
        cache.put(key, b"\xaa" * 32)
        cache.evict(key)
        assert cache.get(key) is None

    def test_evict_missing_key_is_noop(self) -> None:
        cache = _make_cache()
        cache.evict(b"\x99" * 32)

    def test_clear_removes_all(self) -> None:
        cache = _make_cache()
        for i in range(5):
            cache.put(bytes([i]) * 32, b"\xaa" * 32)
        cache.clear()
        for i in range(5):
            assert cache.get(bytes([i]) * 32) is None


class TestLockedTTLCacheLoading:
    def test_get_or_load_uses_loader_on_miss(self) -> None:
        cache = _make_cache()
        calls = 0

        def loader() -> bytes:
            nonlocal calls
            calls += 1
            return b"\xaa" * 32

        assert cache.get_or_load("key", loader) == b"\xaa" * 32
        assert calls == 1

    def test_get_or_load_uses_cached_value_on_hit(self) -> None:
        cache = _make_cache()
        calls = 0

        def loader() -> bytes:
            nonlocal calls
            calls += 1
            return b"\xaa" * 32

        cache.get_or_load("key", loader)
        assert cache.get_or_load("key", loader) == b"\xaa" * 32
        assert calls == 1

    def test_disabled_cache_calls_loader_every_time(self) -> None:
        cache = _make_cache()
        cache.set_enabled(False)
        calls = 0

        def loader() -> bytes:
            nonlocal calls
            calls += 1
            return bytes([calls]) * 32

        assert cache.get_or_load("key", loader) == b"\x01" * 32
        assert cache.get_or_load("key", loader) == b"\x02" * 32
        assert calls == 2


class TestLockedTTLCacheTTL:
    def test_expired_entry_returns_none(self) -> None:
        fake_time = 0.0

        def tick() -> float:
            return fake_time

        cache = _make_cache(ttl_seconds=1)
        ttl_cache: TTLCache[Hashable, bytes] = TTLCache(maxsize=100, ttl=1, timer=tick)
        cache._cache = ttl_cache
        key = b"\x01" * 32
        cache.put(key, b"\xaa" * 32)

        fake_time = 2.0

        assert cache.get(key) is None

    def test_not_yet_expired_returns_value(self) -> None:
        cache = _make_cache()
        key = b"\x01" * 32
        value = b"\xaa" * 32
        cache.put(key, value)
        assert cache.get(key) == value


class TestLockedTTLCacheOverwrite:
    def test_put_overwrites_existing(self) -> None:
        cache = _make_cache()
        key = b"\x01" * 32
        cache.put(key, b"\xaa" * 32)
        cache.put(key, b"\xbb" * 32)
        assert cache.get(key) == b"\xbb" * 32


class TestLockedTTLCacheDisabled:
    def test_disabled_cache_does_not_return_put_value(self) -> None:
        cache = _make_cache()
        key = b"\x01" * 32

        cache.set_enabled(False)
        cache.put(key, b"\xaa" * 32)

        assert cache.get(key) is None
        assert len(cache) == 0

    def test_disabling_cache_clears_existing_values(self) -> None:
        cache = _make_cache()
        key = b"\x01" * 32
        cache.put(key, b"\xaa" * 32)

        cache.set_enabled(False)

        assert cache.get(key) is None
        assert len(cache) == 0


class TestCryptoCacheNamespace:
    def test_container_exposes_named_crypto_caches(self) -> None:
        cache = create_app_cache().crypto
        linkage_key = _make_linkage_key()
        survey_key_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
        session_id = uuid.UUID("00000000-0000-0000-0000-000000000004")

        cache.current_linkage_key.put("current", linkage_key)
        cache.linkage_keys_by_version.put(1, linkage_key)
        cache.survey_branch_keys.put(survey_key_id, b"\xaa" * 32)
        cache.session_deks.put(session_id, b"\xbb" * 32)

        assert cache.current_linkage_key.get("current") == linkage_key
        assert cache.linkage_keys_by_version.get(1) == linkage_key
        assert cache.survey_branch_keys.get(survey_key_id) == b"\xaa" * 32
        assert cache.session_deks.get(session_id) == b"\xbb" * 32

    def test_can_disable_all_named_crypto_caches(self) -> None:
        app_cache = create_app_cache()
        cache = app_cache.crypto
        survey_key_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
        session_id = uuid.UUID("00000000-0000-0000-0000-000000000004")

        app_cache.set_enabled(False)

        cache.survey_branch_keys.put(survey_key_id, b"\xaa" * 32)
        cache.session_deks.put(session_id, b"\xbb" * 32)

        assert cache.survey_branch_keys.get(survey_key_id) is None
        assert cache.session_deks.get(session_id) is None


def _settings_with_cache_enabled(enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(
        flowform=SimpleNamespace(
            encryption=SimpleNamespace(key_cache_enabled=enabled),
        ),
    )


def _make_linkage_key() -> LinkageKey:
    return LinkageKey(
        version=1,
        secret=b"\x03" * 32,
        aws_version_id="11111111-1111-1111-1111-111111111111",
    )


def _make_session_write_context() -> SessionWriteContext:
    return SessionWriteContext(
        session_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        project_id=1,
        survey_id=2,
        survey_version_id=3,
        session_locator=b"\x01" * 32,
        envelope_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        plaintext_session_dek=b"\x02" * 32,
        crypto_version=1,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
        linkage_key=_make_linkage_key(),
    )


class TestSessionCacheNamespace:
    def test_container_exposes_write_context_cache(self) -> None:
        cache = create_app_cache().sessions
        ctx = _make_session_write_context()

        cache.write_context.put(b"token-hash", ctx)

        assert cache.write_context.get(b"token-hash") == ctx

    def test_can_disable_write_context_cache(self) -> None:
        app_cache = create_app_cache()
        cache = app_cache.sessions

        app_cache.set_enabled(False)

        cache.write_context.put(b"token-hash", _make_session_write_context())

        assert cache.write_context.get(b"token-hash") is None

    def test_init_app_uses_key_cache_enabled_setting(self) -> None:
        app = Flask(__name__)
        app.extensions["settings"] = _settings_with_cache_enabled(False)
        cache = create_app_cache()

        cache.init_app(app)
        cache.sessions.write_context.put(b"token-hash", _make_session_write_context())

        assert cache.sessions.write_context.get(b"token-hash") is None

    def test_init_app_registers_cache_registry(self) -> None:
        app = Flask(__name__)
        app.extensions["settings"] = _settings_with_cache_enabled(True)
        registry = create_app_cache()
        ctx = _make_session_write_context()

        registry.init_app(app)
        app.extensions[EXTENSION_KEY].sessions.write_context.put(b"token-hash", ctx)

        assert app.extensions[EXTENSION_KEY].sessions.write_context.get(b"token-hash") == ctx
