"""App-wide crypto service graph construction.

This module owns construction of crypto service instances and their AWS clients.
It does not prewarm key material; KMS and Secrets Manager are still called only
when a service needs a key that is not already cached.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from flask import Flask

from app.core.config import EncryptionSettings, Settings
from app.crypto.cache import CryptoKeyCache
from app.crypto.services.answer_crypto_service import AnswerCryptoService
from app.crypto.services.linkage_key_service import LinkageKeyService
from app.crypto.services.locator_service import LocatorService
from app.crypto.services.session_dek_service import SessionDEKService
from app.crypto.services.survey_branch_key_service import SurveyBranchKeyService

logger = logging.getLogger(__name__)

CRYPTO_SERVICES_EXTENSION_KEY = "crypto_services"


@dataclass(frozen=True, slots=True)
class CryptoServices:
    """Pre-wired crypto service instances."""

    linkage_key_service: LinkageKeyService
    locator_service: LocatorService
    dek_service: SessionDEKService
    answer_crypto_service: AnswerCryptoService
    survey_branch_key_service: SurveyBranchKeyService | None = None


def build_crypto_service_graph(
    enc: EncryptionSettings,
    *,
    cache: CryptoKeyCache,
) -> CryptoServices:
    """Construct the full crypto service graph."""
    linkage_key_service = LinkageKeyService(
        cache=cache.linkage_keys,
        linkage_secret_arn=enc.linkage_secret_arn,
        region=enc.aws_region,
        access_key_id=enc.aws_access_key_id,
        secret_access_key=enc.aws_secret_access_key,
    )

    locator_service = LocatorService(linkage_key_service=linkage_key_service)

    dek_service = SessionDEKService(cache=cache.session_deks)

    survey_branch_key_service = SurveyBranchKeyService(
        cache=cache.survey_branch_keys,
        kms_key_arn=enc.kms_key_arn,
        region=enc.aws_region,
        access_key_id=enc.aws_access_key_id,
        secret_access_key=enc.aws_secret_access_key,
    )

    answer_crypto_service = AnswerCryptoService()

    return CryptoServices(
        linkage_key_service=linkage_key_service,
        locator_service=locator_service,
        dek_service=dek_service,
        answer_crypto_service=answer_crypto_service,
        survey_branch_key_service=survey_branch_key_service,
    )


def init_crypto_services(app: Flask, *, cache: CryptoKeyCache) -> None:
    """Register app-wide crypto services, without fetching any key material."""
    settings: Settings = app.extensions["settings"]
    enc = settings.flowform.encryption
    if enc is None:
        logger.debug("Crypto services not initialized: encryption settings not configured")
        return

    app.extensions[CRYPTO_SERVICES_EXTENSION_KEY] = build_crypto_service_graph(
        enc,
        cache=cache,
    )
    logger.debug("Crypto services initialized")
