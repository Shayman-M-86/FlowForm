"""Unit tests for worker-local crypto key caches."""

from __future__ import annotations

from collections.abc import Hashable

from cachetools import TTLCache

from app.crypto.cache import CryptoKeyCache, LockedTTLCache


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


class TestCryptoKeyCache:
    def test_container_exposes_named_crypto_caches(self) -> None:
        cache = CryptoKeyCache()

        cache.survey_branch_keys.put("survey-key-id", b"\xaa" * 32)
        cache.session_deks.put("session-id", b"\xbb" * 32)

        assert cache.survey_branch_keys.get("survey-key-id") == b"\xaa" * 32
        assert cache.session_deks.get("session-id") == b"\xbb" * 32

    def test_can_disable_all_named_crypto_caches(self) -> None:
        cache = CryptoKeyCache()
        cache.set_enabled(False)

        cache.survey_branch_keys.put("survey-key-id", b"\xaa" * 32)
        cache.session_deks.put("session-id", b"\xbb" * 32)

        assert cache.survey_branch_keys.get("survey-key-id") is None
        assert cache.session_deks.get("session-id") is None
