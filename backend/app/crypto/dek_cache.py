"""Worker-local DEK cache with TTL and eviction."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass(slots=True)
class _CacheEntry:
    plaintext_dek: bytes
    expires_at: float


class DekCache:
    """In-memory cache for plaintext DEKs keyed by session locator.

    Thread-safe. Evicts on session completion, expiry, abandonment,
    and worker restart (cache is ephemeral by design).
    """

    def __init__(self, default_ttl_seconds: float = 3600.0) -> None:
        self._store: dict[bytes, _CacheEntry] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl_seconds

    def get(self, session_locator: bytes) -> bytes | None:
        """Return cached plaintext DEK or None if missing/expired."""
        with self._lock:
            entry = self._store.get(session_locator)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[session_locator]
                return None
            return entry.plaintext_dek

    def put(
        self,
        session_locator: bytes,
        plaintext_dek: bytes,
        ttl_seconds: float | None = None,
    ) -> None:
        """Cache a plaintext DEK with the given TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        with self._lock:
            self._store[session_locator] = _CacheEntry(
                plaintext_dek=plaintext_dek,
                expires_at=time.monotonic() + ttl,
            )

    def evict(self, session_locator: bytes) -> None:
        """Remove a specific session's DEK from the cache."""
        with self._lock:
            self._store.pop(session_locator, None)

    def clear(self) -> None:
        """Remove all cached DEKs (worker restart scenario)."""
        with self._lock:
            self._store.clear()
