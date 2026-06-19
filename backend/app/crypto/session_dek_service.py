"""Service for managing plaintext session DEKs unwrapped from AWS KMS."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import SecretStr

from app.crypto.errors import KmsError, SessionDEKUnavailableError
from app.crypto.kms import unwrap_dek

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _CacheEntry:
    plaintext_dek: bytes
    expires_at: float


class SessionDEKService:
    """Unwraps, caches, and serves plaintext session DEKs."""

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
