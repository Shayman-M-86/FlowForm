"""Service for managing plaintext session DEKs.

SessionDEKService owns the session-specific DEK lifecycle below the survey
branch key:

Create path:
    1. Generate 32 random bytes as the plaintext session DEK.
    2. Wrap it locally with AES-256-GCM using the plaintext survey branch key.
    3. Return plaintext and wrapped session DEK material.
    4. Cache the plaintext session DEK for the active session window.

Read path:
    1. Check the worker-local session DEK cache.
    2. On miss, ask the caller for the plaintext survey branch key.
    3. Locally unwrap the stored session DEK.
    4. Cache the plaintext session DEK until the session expires.

This service does not call KMS, derive locators, query the database, or
encrypt answer payloads.
"""

from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.crypto.errors import SessionDEKUnavailableError
from app.crypto.nonces import generate_nonce

logger = logging.getLogger(__name__)


_KEY_LENGTH = 32
_NONCE_LENGTH = 12


@dataclass(frozen=True, slots=True)
class NewSessionDEK:
    """Returned when provisioning a session DEK."""

    plaintext_dek: bytes
    wrapped_session_dek: bytes

    @property
    def wrapped_dek(self) -> bytes:
        """Compatibility alias during the branch-key refactor."""
        return self.wrapped_session_dek


@dataclass(slots=True)
class _CacheEntry:
    plaintext_dek: bytes
    expires_at: float


class SessionDEKService:
    """Creates, unwraps, caches, and serves plaintext session DEKs."""

    def __init__(self, **_: object) -> None:
        self._lock = threading.Lock()
        self._cache: dict[uuid.UUID, _CacheEntry] = {}

    def create_for_session(
        self,
        session_id: uuid.UUID,
        survey_branch_key: bytes,
        expires_at: datetime,
        *,
        wrap_aad: bytes,
    ) -> NewSessionDEK:
        """Generate a new plaintext session DEK and wrap it locally."""
        plaintext_dek = os.urandom(_KEY_LENGTH)
        try:
            wrapped_session_dek = _wrap_session_dek(
                plaintext_dek=plaintext_dek,
                survey_branch_key=survey_branch_key,
                aad=wrap_aad,
            )
        except Exception as exc:
            logger.error("session_dek wrap_failed session_id=%s", session_id)
            raise SessionDEKUnavailableError() from exc

        self._cache_plaintext(session_id, plaintext_dek, expires_at)
        return NewSessionDEK(
            plaintext_dek=plaintext_dek,
            wrapped_session_dek=wrapped_session_dek,
        )

    def get_for_session(
        self,
        session_id: uuid.UUID,
        wrapped_session_dek: bytes,
        expires_at: datetime,
        *,
        wrap_aad: bytes,
        survey_branch_key_loader: Callable[[], bytes],
    ) -> bytes:
        """Return the plaintext session DEK, unwrapping locally on cache miss."""
        now_mono = time.monotonic()
        with self._lock:
            entry = self._cache.get(session_id)
            if entry is not None and entry.expires_at > now_mono:
                logger.debug("session_dek source=cache session_id=%s", session_id)
                return entry.plaintext_dek

        try:
            logger.debug("session_dek source=local_unwrap session_id=%s", session_id)
            plaintext_dek = _unwrap_session_dek(
                wrapped_session_dek=wrapped_session_dek,
                survey_branch_key=survey_branch_key_loader(),
                aad=wrap_aad,
            )
        except Exception as exc:
            logger.error("session_dek unwrap_failed session_id=%s", session_id)
            raise SessionDEKUnavailableError() from exc

        self._cache_plaintext(session_id, plaintext_dek, expires_at)
        return plaintext_dek

    def clear_for_session(self, session_id: uuid.UUID) -> None:
        """Remove the cached DEK for a session."""
        with self._lock:
            self._cache.pop(session_id, None)

    def clear_expired(self) -> None:
        """Remove all expired entries from cache."""
        now = time.monotonic()
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.expires_at <= now]
            for k in expired:
                del self._cache[k]

    def _cache_plaintext(
        self,
        session_id: uuid.UUID,
        plaintext_dek: bytes,
        expires_at: datetime,
    ) -> None:
        ttl = self._datetime_to_ttl(expires_at)
        if ttl <= 0:
            return

        with self._lock:
            self._cache[session_id] = _CacheEntry(
                plaintext_dek=plaintext_dek,
                expires_at=time.monotonic() + ttl,
            )

    @staticmethod
    def _datetime_to_ttl(expires_at: datetime) -> float:
        delta = expires_at - datetime.now(UTC)
        return max(delta.total_seconds(), 0.0)


def _wrap_session_dek(
    *,
    plaintext_dek: bytes,
    survey_branch_key: bytes,
    aad: bytes,
) -> bytes:
    _validate_key("session DEK", plaintext_dek)
    _validate_key("survey branch key", survey_branch_key)
    nonce = generate_nonce()
    ciphertext = AESGCM(survey_branch_key).encrypt(nonce, plaintext_dek, aad)
    return nonce + ciphertext


def _unwrap_session_dek(
    *,
    wrapped_session_dek: bytes,
    survey_branch_key: bytes,
    aad: bytes,
) -> bytes:
    _validate_key("survey branch key", survey_branch_key)
    if len(wrapped_session_dek) <= _NONCE_LENGTH:
        raise ValueError("wrapped session DEK is too short")

    nonce = wrapped_session_dek[:_NONCE_LENGTH]
    ciphertext = wrapped_session_dek[_NONCE_LENGTH:]
    plaintext_dek = AESGCM(survey_branch_key).decrypt(nonce, ciphertext, aad)
    _validate_key("session DEK", plaintext_dek)
    return plaintext_dek


def _validate_key(label: str, key: bytes) -> None:
    if len(key) != _KEY_LENGTH:
        raise ValueError(f"{label} must be {_KEY_LENGTH} bytes, got {len(key)}")
