"""Build the crypto service graph from EncryptionSettings.

Centralises AWS credential wiring so that orchestration services receive
ready-to-use crypto service instances instead of threading credentials
through every call site.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import EncryptionSettings, current_settings
from app.crypto.services import (
    AnswerCryptoService,
    LinkageKeyService,
    LocatorService,
    SessionDEKService,
)
from app.domain.errors import SessionInvalidError


@dataclass(frozen=True, slots=True)
class CryptoServices:
    """Pre-wired crypto service instances."""

    linkage_key_service: LinkageKeyService
    locator_service: LocatorService
    dek_service: SessionDEKService
    answer_crypto_service: AnswerCryptoService


def _resolve_encryption_settings(enc: EncryptionSettings | None) -> EncryptionSettings:
    if enc is not None:
        return enc
    settings = current_settings()
    enc_cfg = settings.flowform.encryption
    if enc_cfg is None:
        raise SessionInvalidError("Encryption settings not configured")
    return enc_cfg


def build_crypto_services(enc: EncryptionSettings | None = None) -> CryptoServices:
    """Construct the full crypto service graph.

    When *enc* is ``None``, settings are read from the Flask app config
    via ``current_settings()``.
    """
    resolved = _resolve_encryption_settings(enc)

    linkage_key_service = LinkageKeyService(
        linkage_secret_arn=resolved.linkage_secret_arn,
        region=resolved.aws_region,
        access_key_id=resolved.aws_access_key_id,
        secret_access_key=resolved.aws_secret_access_key,
        cache_ttl_seconds=resolved.linkage_key_cache_ttl_seconds,
    )

    locator_service = LocatorService(linkage_key_service=linkage_key_service)

    dek_service = SessionDEKService(
        region=resolved.aws_region,
        access_key_id=resolved.aws_access_key_id,
        secret_access_key=resolved.aws_secret_access_key,
    )

    answer_crypto_service = AnswerCryptoService()

    return CryptoServices(
        linkage_key_service=linkage_key_service,
        locator_service=locator_service,
        dek_service=dek_service,
        answer_crypto_service=answer_crypto_service,
    )
