"""Service for managing plaintext session DEKs via AWS KMS.

SessionDEKService handles both sides of DEK lifecycle:

Create path (new session):
    1. Generate 32 random bytes as the plaintext DEK.
    2. Wrap (encrypt) the DEK via KMS using the provided key ARN and
       encryption context.
    3. Return both the plaintext DEK and the wrapped (ciphertext) blob.
    4. Optionally cache the plaintext DEK for the session window.

Read path (existing session):
    1. Check the in-memory cache for a previously unwrapped DEK.
    2. If not cached, unwrap (decrypt) the stored wrapped DEK via KMS.
    3. Cache the plaintext DEK until the session expires.
    4. Return the plaintext DEK for answer encrypt/decrypt operations.

The cache is per-worker, keyed by (session_id, kms_key_arn), and bounded
by session expiry. DEKs should be cleared when a session is completed,
abandoned, or deleted.

This service does not manage nonces, answer payloads, locators, or
database records.
"""

from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import SecretStr

from app.crypto.errors import KmsError, SessionDEKUnavailableError
from app.crypto.kms import unwrap_dek, wrap_dek

logger = logging.getLogger(__name__)


_DEK_LENGTH = 32


@dataclass(frozen=True, slots=True)
class NewSessionDEK:
    """Returned when provisioning a DEK for a new session."""

    plaintext_dek: bytes
    wrapped_dek: bytes


@dataclass(slots=True)
class _CacheEntry:
    plaintext_dek: bytes
    expires_at: float


class SessionDEKService:
    """Creates, unwraps, caches, and serves plaintext session DEKs."""

    def __init__(
        self,
        *,
        region: str,
        access_key_id: SecretStr,
        secret_access_key: SecretStr,
    ) -> None:
        self._region = region
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key

        self._lock = threading.Lock()
        self._cache: dict[tuple[uuid.UUID, str], _CacheEntry] = {}

    def create_for_session(
        self,
        session_id: uuid.UUID,
        kms_key_arn: str,
        expires_at: datetime,
        *,
        encryption_context: dict[str, str] | None = None,
    ) -> NewSessionDEK:
        """Generate a new plaintext DEK and wrap it via KMS for storage."""
        plaintext_dek = os.urandom(_DEK_LENGTH)
        context = encryption_context if encryption_context is not None else {}
        try:
            wrapped_dek = wrap_dek(
                plaintext_dek,
                kms_key_arn,
                context,
                region=self._region,
                access_key_id=self._access_key_id,
                secret_access_key=self._secret_access_key,
            )
        except KmsError as exc:
            logger.error("DEK wrap failed for session %s", session_id)
            raise SessionDEKUnavailableError() from exc

        ttl = self._datetime_to_ttl(expires_at)
        if ttl > 0:
            now_mono = time.monotonic()
            with self._lock:
                self._cache[(session_id, kms_key_arn)] = _CacheEntry(
                    plaintext_dek=plaintext_dek,
                    expires_at=now_mono + ttl,
                )

        return NewSessionDEK(plaintext_dek=plaintext_dek, wrapped_dek=wrapped_dek)

    def get_for_session(
        self,
        session_id: uuid.UUID,
        wrapped_dek: bytes,
        kms_key_arn: str,
        expires_at: datetime,
        *,
        encryption_context: dict[str, str] | None = None,
    ) -> bytes:
        """Return the plaintext DEK for a session, unwrapping via KMS if needed."""
        cache_key = (session_id, kms_key_arn)
        now_mono = time.monotonic()
        with self._lock:
            entry = self._cache.get(cache_key)
            if entry is not None and entry.expires_at > now_mono:
                return entry.plaintext_dek

        context = encryption_context if encryption_context is not None else {}
        try:
            plaintext_dek = unwrap_dek(
                wrapped_dek,
                kms_key_arn,
                context,
                region=self._region,
                access_key_id=self._access_key_id,
                secret_access_key=self._secret_access_key,
            )
        except KmsError as exc:
            logger.error("DEK unwrap failed for session %s", session_id)
            raise SessionDEKUnavailableError() from exc

        ttl = self._datetime_to_ttl(expires_at)
        if ttl > 0:
            with self._lock:
                self._cache[cache_key] = _CacheEntry(
                    plaintext_dek=plaintext_dek,
                    expires_at=now_mono + ttl,
                )

        return plaintext_dek

    def clear_for_session(self, session_id: uuid.UUID) -> None:
        """Remove all cached DEKs for a session."""
        with self._lock:
            keys = [k for k in self._cache if k[0] == session_id]
            for k in keys:
                del self._cache[k]

    def clear_expired(self) -> None:
        """Remove all expired entries from cache."""
        now = time.monotonic()
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.expires_at <= now]
            for k in expired:
                del self._cache[k]

    @staticmethod
    def _datetime_to_ttl(expires_at: datetime) -> float:
        delta = expires_at - datetime.now(UTC)
        return max(delta.total_seconds(), 0.0)
