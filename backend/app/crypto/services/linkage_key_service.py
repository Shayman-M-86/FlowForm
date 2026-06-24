"""Service for managing versioned linkage keys used in locator derivation.

Uses a single Secrets Manager secret with multiple versions. The AWSCURRENT
stage always points to the active key. Each version's value is a JSON object:

    {"version": <int>, "secret_b64": "<base64-encoded key>"}

The application-level ``version`` field inside the payload is the version
number stored alongside sessions. The AWS ``VersionId`` is the identifier
Secrets Manager assigns to each secret revision and is used to retrieve
specific versions.
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.crypto.cache import LockedTTLCache
from app.crypto.errors import (
    LinkageKeyError,
    LinkageKeyUnavailableError,
    LinkageSecretError,
)
from app.crypto.secrets import (
    SecretValue,
    _build_secretsmanager_client,
    get_linkage_secret,
)
from app.db.error_handling import commit_with_err_handle
from app.repositories.linkage_key_versions_repo import (
    get_aws_version_id,
    insert_version,
    version_exists,
)

logger = logging.getLogger(__name__)

_MIN_SECRET_BYTES = 32
_CURRENT_LINKAGE_KEY_CACHE_KEY = "current"


@dataclass(frozen=True, slots=True)
class LinkageKey:
    """A versioned linkage secret."""

    version: int
    secret: bytes
    aws_version_id: str


class LinkageKeyService:
    """Fetches, validates, and caches versioned linkage keys from Secrets Manager.

    All versions live in a single Secrets Manager secret. ``get_linkage_key()``
    fetches AWSCURRENT (the active key). ``get_linkage_key_by_version()``
    checks the cache first, then fetches by AWS VersionId if the requested
    app-level version was seen before.
    """

    def __init__(
        self,
        *,
        cache: LockedTTLCache[LinkageKey],
        linkage_secret_arn: str,
        region: str,
        access_key_id: SecretStr,
        secret_access_key: SecretStr,
    ) -> None:
        self._cache = cache
        self._linkage_secret_arn = linkage_secret_arn
        self._region = region
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._secrets_client = _build_secretsmanager_client(
            region,
            access_key_id,
            secret_access_key,
        )

        self._version_id_lock = threading.Lock()
        self._version_id_map: dict[int, str] = {}

    def get_linkage_key(self, db: Session) -> LinkageKey:
        """Return the current (AWSCURRENT) linkage key.

        If the version is not yet in the ``linkage_key_versions`` table,
        inserts it and marks it as current.
        """
        cached = self._cache.get(_CURRENT_LINKAGE_KEY_CACHE_KEY)
        if cached is not None:
            return cached

        logger.debug("linkage_key source=secrets_manager_api_lookup context=current")
        sv = self._fetch_secret(version_stage="AWSCURRENT", context="current")
        key = self._parse_and_validate(sv)
        self._cache.put(_CURRENT_LINKAGE_KEY_CACHE_KEY, key)
        self._cache.put(key.version, key)
        self._record_version_id(key.version, key.aws_version_id)
        self._ensure_db_row(db, key, is_current=True)
        return key

    def get_linkage_key_by_version(self, version: int, db: Session) -> LinkageKey:
        """Return the linkage key for a specific application-level version.

        Resolves the AWS VersionId via the in-memory map first, then falls
        back to the ``linkage_key_versions`` database table.
        """
        cached = self._cache.get(version)
        if cached is not None:
            return cached

        with self._version_id_lock:
            aws_version_id = self._version_id_map.get(version)
        version_id_source = "memory"

        if aws_version_id is None:
            db_version_id = get_aws_version_id(db, version)
            if db_version_id is not None:
                aws_version_id = str(db_version_id)
                version_id_source = "database"

        if aws_version_id is not None:
            logger.debug(
                "linkage_key source=secrets_manager_api_lookup version=%s version_id_source=%s context=v%s",
                version,
                version_id_source,
                version,
            )
            sv = self._fetch_secret(
                version_id=aws_version_id, context=f"v{version}"
            )
        else:
            raise LinkageKeyError(
                f"Linkage key v{version} not found in cache or database"
            )

        key = self._parse_and_validate(sv)

        if key.version != version:
            raise LinkageKeyError(
                f"Requested linkage key v{version} but secret contains v{key.version}"
            )

        self._cache.put(key.version, key)
        self._record_version_id(key.version, key.aws_version_id)
        return key

    def _record_version_id(self, version: int, aws_version_id: str) -> None:
        with self._version_id_lock:
            self._version_id_map[version] = aws_version_id

    def _parse_and_validate(self, sv: SecretValue) -> LinkageKey:
        try:
            data: Any = json.loads(sv.secret_string)
        except (json.JSONDecodeError, TypeError) as exc:
            raise LinkageKeyError("Linkage secret is not valid JSON") from exc

        if not isinstance(data, dict):
            raise LinkageKeyError("Linkage secret is not a JSON object")

        version = data.get("version")
        if not isinstance(version, int) or version < 1:
            raise LinkageKeyError("Linkage secret missing or invalid 'version'")

        secret_b64 = data.get("secret_b64")
        if not isinstance(secret_b64, str) or not secret_b64:
            raise LinkageKeyError(f"Linkage secret v{version} missing 'secret_b64'")

        try:
            secret_bytes = base64.b64decode(secret_b64)
        except Exception as exc:
            raise LinkageKeyError(f"Invalid base64 in linkage secret v{version}") from exc

        if len(secret_bytes) == 0:
            raise LinkageKeyError(f"Decoded secret for v{version} is empty")
        if len(secret_bytes) < _MIN_SECRET_BYTES:
            raise LinkageKeyError(
                f"Decoded secret for v{version} is too short ({len(secret_bytes)} bytes, "
                f"minimum {_MIN_SECRET_BYTES})"
            )

        return LinkageKey(
            version=version, secret=secret_bytes, aws_version_id=sv.version_id
        )

    def _ensure_db_row(self, db: Session, key: LinkageKey, *, is_current: bool) -> None:
        if version_exists(db, key.version):
            return
        insert_version(
            db,
            version=key.version,
            aws_secret_id=self._linkage_secret_arn,
            aws_secret_version_id=uuid.UUID(key.aws_version_id),
            is_current=is_current,
        )
        commit_with_err_handle(db)

    def _fetch_secret(
        self,
        *,
        version_id: str | None = None,
        version_stage: str | None = None,
        context: str,
    ) -> SecretValue:
        try:
            return get_linkage_secret(
                self._linkage_secret_arn,
                version_id=version_id,
                version_stage=version_stage,
                region=self._region,
                access_key_id=self._access_key_id,
                secret_access_key=self._secret_access_key,
                client=self._secrets_client,
            )
        except LinkageSecretError as exc:
            logger.error("Failed to fetch linkage key (%s) from Secrets Manager", context)
            raise LinkageKeyUnavailableError() from exc
