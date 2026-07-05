"""Versioned linkage key access."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.config import current_settings
from app.crypto._internal.errors import LinkageKeyError
from app.crypto._internal.linkage_secrets import fetch_linkage_secret_from_aws
from app.crypto.models import LinkageKey
from app.db.error_handling import commit_with_err_handle
from app.repositories import linkage_key_versions_repo as linkage_key_repo

if TYPE_CHECKING:
    from app.cache import AppCache
    from app.crypto._internal.client_extension import CryptoClients

_CURRENT_CACHE_KEY = "current"


def get_current_linkage_key(
    db: Session,
    *,
    cache: AppCache,
    clients: CryptoClients,
) -> LinkageKey:
    """Return the current linkage key.

    Checks cache first, then fetches AWSCURRENT from Secrets Manager
    on miss and persists the version mapping.
    """
    crypto_cache = cache.crypto

    cached = crypto_cache.current_linkage_key.get(_CURRENT_CACHE_KEY)
    if cached is not None:
        return cached

    secret = fetch_linkage_secret_from_aws(
        version_stage="AWSCURRENT",
        client=clients.secretsmanager,
    )
    key = LinkageKey.from_secret_value(secret)

    crypto_cache.current_linkage_key.put(_CURRENT_CACHE_KEY, key)
    crypto_cache.linkage_keys_by_version.put(key.version, key)

    _ensure_version_row(db, key)

    return key


def get_linkage_key_by_version(
    version: int,
    db: Session,
    *,
    cache: AppCache,
    clients: CryptoClients,
) -> LinkageKey:
    """Return a linkage key by app-level version.

    Checks cache first, then looks up the AWS version ID from the DB
    and fetches that specific secret version from Secrets Manager.
    """
    crypto_cache = cache.crypto

    cached = crypto_cache.linkage_keys_by_version.get(version)
    if cached is not None:
        return cached

    aws_version_id = linkage_key_repo.get_aws_version_id(db, version)
    if aws_version_id is None:
        raise LinkageKeyError(f"Linkage key v{version} not found")

    secret = fetch_linkage_secret_from_aws(
        version_id=str(aws_version_id),
        client=clients.secretsmanager,
    )
    key = LinkageKey.from_secret_value(secret)

    if key.version != version:
        raise LinkageKeyError(f"Requested linkage key v{version} but secret contains v{key.version}")

    crypto_cache.linkage_keys_by_version.put(key.version, key)

    return key


def _ensure_version_row(db: Session, key: LinkageKey) -> None:
    """Persist the app version -> AWS secret version mapping if missing."""
    if linkage_key_repo.version_exists(db, key.version):
        return

    linkage_key_repo.insert_version(
        db,
        version=key.version,
        aws_secret_id=current_settings().flowform.encryption.linkage_secret_arn,
        aws_secret_version_id=uuid.UUID(key.aws_version_id),
        is_current=True,
    )
    commit_with_err_handle(db)
