"""Access the crypto service graph from public-submission code.

Construction lives in ``app.crypto.services.provider``. This module keeps the
public-submission import path stable while preferring the app-wide service graph
registered during extension startup.
"""

from __future__ import annotations

from typing import cast

from flask import current_app, has_app_context

from app.core.config import EncryptionSettings, current_settings
from app.crypto.cache import CryptoKeyCache
from app.crypto.services.provider import (
    CRYPTO_SERVICES_EXTENSION_KEY,
    CryptoServices,
    build_crypto_service_graph,
)
from app.domain.errors import SessionInvalidError

_fallback_crypto_key_cache = CryptoKeyCache()


def _resolve_encryption_settings(enc: EncryptionSettings | None) -> EncryptionSettings:
    if enc is not None:
        return enc
    settings = current_settings()
    enc_cfg = settings.flowform.encryption
    if enc_cfg is None:
        raise SessionInvalidError("Encryption settings not configured")
    return enc_cfg


def _resolve_cache(cache: CryptoKeyCache | None) -> CryptoKeyCache:
    if cache is not None:
        return cache
    if has_app_context():
        registered = current_app.extensions.get("crypto_key_cache")
        if registered is not None:
            return cast(CryptoKeyCache, registered)
    return _fallback_crypto_key_cache


def build_crypto_services(
    enc: EncryptionSettings | None = None,
    *,
    cache: CryptoKeyCache | None = None,
) -> CryptoServices:
    """Construct the full crypto service graph.

    When *enc* is ``None``, settings are read from the Flask app config
    via ``current_settings()``.  When *cache* is ``None``, the app-wide
    ``CryptoKeyCache`` registered in ``create_app`` is used.
    """
    resolved = _resolve_encryption_settings(enc)
    resolved_cache = _resolve_cache(cache)
    return build_crypto_service_graph(resolved, cache=resolved_cache)


def get_crypto_services(
    enc: EncryptionSettings | None = None,
    *,
    cache: CryptoKeyCache | None = None,
) -> CryptoServices:
    """Return app-wide crypto services, or build an isolated graph for overrides."""
    if enc is None and cache is None and has_app_context():
        crypto = current_app.extensions.get(CRYPTO_SERVICES_EXTENSION_KEY)
        if crypto is not None:
            return cast(CryptoServices, crypto)

    return build_crypto_services(enc, cache=cache)
