"""Build the crypto service graph from EncryptionSettings.

Centralises AWS credential wiring so that orchestration services receive
ready-to-use crypto service instances instead of threading credentials
through every call site.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.config import EncryptionSettings, current_settings
from app.core.extensions import crypto_key_cache
from app.crypto.services import (
    AnswerCryptoService,
    LinkageKeyService,
    LocatorService,
    SessionDEKService,
    SurveyBranchKeyService,
)
from app.domain.errors import SessionInvalidError

if TYPE_CHECKING:
    from app.crypto.cache import CryptoKeyCache


@dataclass(frozen=True, slots=True)
class CryptoServices:
    """Pre-wired crypto service instances."""

    linkage_key_service: LinkageKeyService
    locator_service: LocatorService
    dek_service: SessionDEKService
    answer_crypto_service: AnswerCryptoService
    survey_branch_key_service: SurveyBranchKeyService | None = None


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
    return crypto_key_cache


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

    linkage_key_service = LinkageKeyService(
        cache=resolved_cache.linkage_keys,
        linkage_secret_arn=resolved.linkage_secret_arn,
        region=resolved.aws_region,
        access_key_id=resolved.aws_access_key_id,
        secret_access_key=resolved.aws_secret_access_key,
    )

    locator_service = LocatorService(linkage_key_service=linkage_key_service)

    dek_service = SessionDEKService(cache=resolved_cache.session_deks)

    survey_branch_key_service = SurveyBranchKeyService(
        cache=resolved_cache.survey_branch_keys,
        kms_key_arn=resolved.kms_key_arn,
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
        survey_branch_key_service=survey_branch_key_service,
    )
