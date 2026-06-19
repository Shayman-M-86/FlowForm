"""Service for managing versioned linkage keys used in locator derivation."""

from __future__ import annotations

import base64
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

from pydantic import SecretStr

from app.crypto.errors import (
    LinkageKeyError,
    LinkageKeyUnavailableError,
    LinkageKeyVersionUnavailableError,
    LinkageSecretError,
)
from app.crypto.secrets import get_linkage_secret

logger = logging.getLogger(__name__)

_MIN_SECRET_BYTES = 32
_DEFAULT_CACHE_TTL_SECONDS = 1800.0  # 30 minutes


@dataclass(frozen=True, slots=True)
class LinkageKey:
    """A versioned linkage secret."""

    version: int
    secret: bytes


@dataclass(slots=True)
class _CacheEntry:
    key: LinkageKey
    expires_at: float


class LinkageKeyService:
    """Fetches, validates, and caches versioned linkage keys from Secrets Manager."""

    def __init__(
        self,
        *,
        current_key_secret_arn: str,
        versioned_key_secret_arn_template: str,
        region: str,
        access_key_id: SecretStr,
        secret_access_key: SecretStr,
        cache_ttl_seconds: float = _DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        self._current_key_secret_arn = current_key_secret_arn
        self._versioned_key_secret_arn_template = versioned_key_secret_arn_template
        self._region = region
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._cache_ttl_seconds = cache_ttl_seconds

        self._lock = threading.RLock()
        self._cache: dict[int, _CacheEntry] = {}
        self._current_version_cache: tuple[int, float] | None = None

    def get_linkage_key(self) -> LinkageKey:
        """Return the current linkage key version and secret."""
        version = self._get_current_version()
        return self.get_linkage_key_by_version(version)

    def get_linkage_key_by_version(self, version: int) -> LinkageKey:
        """Return the linkage key for a specific application-level version."""
        now = time.monotonic()
        with self._lock:
            entry = self._cache.get(version)
            if entry is not None and entry.expires_at > now:
                return entry.key

        key = self._fetch_versioned_key(version)

        with self._lock:
            self._cache[version] = _CacheEntry(
                key=key,
                expires_at=time.monotonic() + self._cache_ttl_seconds,
            )
        return key

    def _get_current_version(self) -> int:
        now = time.monotonic()
        with self._lock:
            if self._current_version_cache is not None:
                version, expires_at = self._current_version_cache
                if expires_at > now:
                    return version

        secret_string = self._fetch_secret(self._current_key_secret_arn, context="current-version-pointer")

        try:
            data: Any = json.loads(secret_string)
        except (json.JSONDecodeError, TypeError) as exc:
            raise LinkageKeyError("Current version pointer is not valid JSON") from exc

        current_version = data.get("current_version") if isinstance(data, dict) else None
        if not isinstance(current_version, int) or current_version < 1:
            raise LinkageKeyError("Current version pointer missing or invalid 'current_version'")

        with self._lock:
            self._current_version_cache = (current_version, time.monotonic() + self._cache_ttl_seconds)
        return current_version

    def _fetch_versioned_key(self, version: int) -> LinkageKey:
        arn = self._versioned_key_secret_arn_template.format(version=version)
        secret_string = self._fetch_secret(arn, context=f"linkage-key-v{version}")

        try:
            data: Any = json.loads(secret_string)
        except (json.JSONDecodeError, TypeError) as exc:
            raise LinkageKeyError(f"Versioned secret for v{version} is not valid JSON") from exc

        if not isinstance(data, dict):
            raise LinkageKeyError(f"Versioned secret for v{version} is not a JSON object")

        stored_version = data.get("version")
        if stored_version != version:
            raise LinkageKeyError(
                f"Version mismatch: requested v{version} but secret contains v{stored_version}"
            )

        secret_b64 = data.get("secret_b64")
        if not isinstance(secret_b64, str) or not secret_b64:
            raise LinkageKeyError(f"Versioned secret for v{version} missing 'secret_b64'")

        try:
            secret_bytes = base64.b64decode(secret_b64)
        except Exception as exc:
            raise LinkageKeyError(f"Invalid base64 in versioned secret for v{version}") from exc

        if len(secret_bytes) == 0:
            raise LinkageKeyError(f"Decoded secret for v{version} is empty")
        if len(secret_bytes) < _MIN_SECRET_BYTES:
            raise LinkageKeyError(
                f"Decoded secret for v{version} is too short ({len(secret_bytes)} bytes, "
                f"minimum {_MIN_SECRET_BYTES})"
            )

        return LinkageKey(version=version, secret=secret_bytes)

    def _fetch_secret(self, secret_arn: str, *, context: str) -> str:
        try:
            return get_linkage_secret(
                secret_arn,
                region=self._region,
                access_key_id=self._access_key_id,
                secret_access_key=self._secret_access_key,
            )
        except LinkageSecretError as exc:
            logger.error("Failed to fetch %s from Secrets Manager", context)
            raise LinkageKeyUnavailableError() from exc
