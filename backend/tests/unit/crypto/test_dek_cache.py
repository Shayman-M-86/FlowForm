"""Unit tests for the worker-local DEK cache."""

from __future__ import annotations

import time
from unittest.mock import patch

from app.crypto.dek_cache import DekCache


class TestDekCacheBasic:
    def test_put_and_get(self) -> None:
        cache = DekCache()
        locator = b"\x01" * 32
        dek = b"\xaa" * 32
        cache.put(locator, dek)
        assert cache.get(locator) == dek

    def test_get_missing_returns_none(self) -> None:
        cache = DekCache()
        assert cache.get(b"\x01" * 32) is None

    def test_evict_removes_entry(self) -> None:
        cache = DekCache()
        locator = b"\x01" * 32
        cache.put(locator, b"\xaa" * 32)
        cache.evict(locator)
        assert cache.get(locator) is None

    def test_evict_missing_key_is_noop(self) -> None:
        cache = DekCache()
        cache.evict(b"\x99" * 32)

    def test_clear_removes_all(self) -> None:
        cache = DekCache()
        for i in range(5):
            cache.put(bytes([i]) * 32, b"\xaa" * 32)
        cache.clear()
        for i in range(5):
            assert cache.get(bytes([i]) * 32) is None


class TestDekCacheTTL:
    def test_expired_entry_returns_none(self) -> None:
        cache = DekCache(default_ttl_seconds=1.0)
        locator = b"\x01" * 32
        cache.put(locator, b"\xaa" * 32)
        with patch("app.crypto.dek_cache.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 2.0
            assert cache.get(locator) is None

    def test_custom_ttl_per_entry(self) -> None:
        cache = DekCache(default_ttl_seconds=3600.0)
        locator = b"\x01" * 32
        cache.put(locator, b"\xaa" * 32, ttl_seconds=0.5)
        with patch("app.crypto.dek_cache.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 1.0
            assert cache.get(locator) is None

    def test_not_yet_expired_returns_value(self) -> None:
        cache = DekCache(default_ttl_seconds=3600.0)
        locator = b"\x01" * 32
        dek = b"\xaa" * 32
        cache.put(locator, dek)
        assert cache.get(locator) == dek


class TestDekCacheOverwrite:
    def test_put_overwrites_existing(self) -> None:
        cache = DekCache()
        locator = b"\x01" * 32
        cache.put(locator, b"\xaa" * 32)
        cache.put(locator, b"\xbb" * 32)
        assert cache.get(locator) == b"\xbb" * 32
