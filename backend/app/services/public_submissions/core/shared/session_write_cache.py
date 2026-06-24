"""In-memory cache for hot-path answer saves.

Stores everything needed to write another answer without re-resolving the
session, re-fetching crypto keys, or re-deriving locators. Keyed by
browser_session_token_hash.

Never cached: decrypted answer values, raw browser tokens, subject identity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from flask import Flask

from app.crypto.cache import LockedTTLCache
from app.crypto.services.linkage_key_service import LinkageKey

logger = logging.getLogger(__name__)

_EXTENSION_KEY = "session_write_cache"


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


_cache: LockedTTLCache[SessionWriteContext] = LockedTTLCache(
    name="session_write_context",
    maxsize=10_000,
    ttl_seconds=1800,
)


def init_app(app: Flask) -> None:
    app.extensions[_EXTENSION_KEY] = _cache
    logger.debug("session_write_cache registered")


def get(token_hash: bytes) -> SessionWriteContext | None:
    return _cache.get(token_hash)


def put(token_hash: bytes, ctx: SessionWriteContext) -> None:
    _cache.put(token_hash, ctx)


def evict(token_hash: bytes) -> None:
    _cache.evict(token_hash)
