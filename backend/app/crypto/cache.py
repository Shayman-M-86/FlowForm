"""App-wide in-memory TTL caches for crypto key material.

Created once when the Flask app starts and reused by all requests handled by
that Python process.  Values expire after a TTL.  Locks prevent two parallel
requests from both calling AWS for the same key.

Do not put this on ``flask.g``; Flask says ``g`` is lost after the
request/app context ends, so it is not for cross-request caching.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Hashable
from threading import Lock
from typing import TYPE_CHECKING

from cachetools import TTLCache
from flask import Flask

if TYPE_CHECKING:
    from app.crypto.services.linkage_key_service import LinkageKey

logger = logging.getLogger(__name__)


class LockedTTLCache[T]:
    """Thread-safe TTL cache with per-key single-flight loading.

    ``TTLCache`` handles expiry.  ``_lock`` protects cache access.
    Per-key locks prevent duplicate AWS calls for the same key.
    """

    def __init__(self, *, name: str, maxsize: int, ttl_seconds: int) -> None:
        self.name = name
        self.enabled = True
        self._cache: TTLCache[Hashable, T] = TTLCache(
            maxsize=maxsize,
            ttl=ttl_seconds,
        )
        self._lock = Lock()
        self._key_locks: dict[Hashable, Lock] = {}

    def get_or_load(self, key: Hashable, loader: Callable[[], T]) -> T:
        """Return cached value or call *loader* exactly once per cache miss."""
        if not self.enabled:
            logger.debug("%s source=cache_disabled key=%r", self.name, key)
            return loader()

        with self._lock:
            try:
                value = self._cache[key]
                logger.debug("%s source=memory_cache key=%r", self.name, key)
                return value
            except KeyError:
                key_lock = self._key_locks.setdefault(key, Lock())

        with key_lock:
            with self._lock:
                try:
                    value = self._cache[key]
                    logger.debug(
                        "%s source=memory_cache_after_wait key=%r", self.name, key,
                    )
                    return value
                except KeyError:
                    pass

            logger.debug("%s source=cache_miss key=%r", self.name, key)
            value = loader()

            with self._lock:
                self._cache[key] = value
                self._key_locks.pop(key, None)

            return value

    def get(self, key: Hashable) -> T | None:
        """Return cached value or ``None`` without loading."""
        if not self.enabled:
            logger.debug("%s source=cache_disabled key=%r", self.name, key)
            return None

        with self._lock:
            try:
                value = self._cache[key]
                logger.debug("%s source=memory_cache key=%r", self.name, key)
                return value
            except KeyError:
                return None

    def put(self, key: Hashable, value: T) -> None:
        """Store a value explicitly."""
        if not self.enabled:
            logger.debug("%s source=cache_disabled key=%r", self.name, key)
            return

        with self._lock:
            self._cache[key] = value

    def evict(self, key: Hashable) -> None:
        """Remove a single key.  No-op if missing."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._cache.clear()
            self._key_locks.clear()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable caching. Disabling also drops existing entries."""
        self.enabled = enabled
        if not enabled:
            self.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


class CryptoKeyCache:
    """Container for all crypto key caches.  Registered as a Flask extension."""

    def __init__(self) -> None:
        self.linkage_keys: LockedTTLCache[LinkageKey] = LockedTTLCache(
            name="linkage_key",
            maxsize=16,
            ttl_seconds=1800,
        )
        self.survey_branch_keys: LockedTTLCache[bytes] = LockedTTLCache(
            name="survey_branch_key",
            maxsize=512,
            ttl_seconds=600,
        )
        self.session_deks: LockedTTLCache[bytes] = LockedTTLCache(
            name="session_dek",
            maxsize=10_000,
            ttl_seconds=1800,
        )

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all crypto key caches."""
        self.linkage_keys.set_enabled(enabled)
        self.survey_branch_keys.set_enabled(enabled)
        self.session_deks.set_enabled(enabled)

    def init_app(self, app: Flask, *, enabled: bool = True) -> None:
        """Register as a Flask extension."""
        self.set_enabled(enabled)
        app.extensions["crypto_key_cache"] = self
        logger.debug("crypto_key_cache enabled=%s", enabled)
