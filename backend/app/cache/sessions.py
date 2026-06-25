"""Session cache definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from app.cache._item import CacheItem
from app.cache._spec import CacheSpec

if TYPE_CHECKING:
    from app.crypto.models import LinkageKey


@dataclass(frozen=True, slots=True)
class SessionWriteContext:
    """Pre-resolved context for a single respondent session."""

    session_id: UUID
    project_id: int
    survey_id: int
    survey_version_id: int
    session_locator: bytes
    envelope_id: UUID
    plaintext_session_dek: bytes
    crypto_version: int
    expires_at: datetime
    linkage_key: LinkageKey


write_context: CacheSpec[bytes, SessionWriteContext] = CacheSpec(
    attr="write_context",
    maxsize=10_000,
    ttl_seconds=1800,
)

caches = (write_context,)


class SessionCacheNamespace(Protocol):
    """Typed public-submission session cache namespace."""

    write_context: CacheItem[bytes, SessionWriteContext]
