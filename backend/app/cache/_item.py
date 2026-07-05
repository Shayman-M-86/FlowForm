"""Typed public wrapper around the low-level TTL cache."""

from __future__ import annotations

from collections.abc import Callable

from app.cache._locked_ttl import LockedTTLCache
from app.cache._spec import CacheSpec


class CacheItem[K, V]:
    """Cache handle that accepts one typed natural lookup key."""

    def __init__(
        self,
        spec: CacheSpec[K, V],
    ) -> None:
        self._make_key = spec.make_key
        self._cache = LockedTTLCache[V](
            name=spec.runtime_name,
            maxsize=spec.maxsize,
            ttl_seconds=spec.ttl_seconds,
        )

    def get(self, key: K) -> V | None:
        return self._cache.get(self._make_key(key))

    def put(self, key: K, value: V) -> None:
        self._cache.put(self._make_key(key), value)

    def get_or_load(self, key: K, loader: Callable[[], V]) -> V:
        return self._cache.get_or_load(self._make_key(key), loader)

    def evict(self, key: K) -> None:
        self._cache.evict(self._make_key(key))

    def clear(self) -> None:
        self._cache.clear()

    def set_enabled(self, enabled: bool) -> None:
        self._cache.set_enabled(enabled)

    def __len__(self) -> int:
        return len(self._cache)
