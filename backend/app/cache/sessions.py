"""Session cache definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from app.cache._item import CacheItem
from app.cache._spec import CacheSpec

if TYPE_CHECKING:
    from app.crypto.models import SessionContext


write_context: CacheSpec[bytes, SessionContext] = CacheSpec(
    attr="write_context",
    maxsize=10_000,
    ttl_seconds=1800,
)

caches = (write_context,)


class SessionCacheNamespace(Protocol):
    """Typed public-submission session cache namespace."""

    write_context: CacheItem[bytes, SessionContext]
