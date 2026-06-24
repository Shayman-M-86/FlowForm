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
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.crypto.cache import LockedTTLCache
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


class SessionDEKService:
    """Creates, unwraps, caches, and serves plaintext session DEKs."""

    def __init__(self, *, cache: LockedTTLCache[bytes]) -> None:
        self._cache = cache

    def create_for_session(
        self,
        session_id: uuid.UUID,
        survey_branch_key: bytes,
        expires_at: datetime,
        *,
        wrap_aad: bytes,
    ) -> NewSessionDEK:
        """Generate a new plaintext session DEK and wrap it locally."""
        _ = expires_at
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

        self._cache.put(session_id, plaintext_dek)
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
        _ = expires_at
        cached = self._cache.get(session_id)
        if cached is not None:
            return cached

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

        self._cache.put(session_id, plaintext_dek)
        return plaintext_dek

    def clear_for_session(self, session_id: uuid.UUID) -> None:
        """Remove the cached DEK for a session."""
        self._cache.evict(session_id)


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
