"""Fetch linkage secrets from AWS Secrets Manager.

Linkage secrets back the locator chain (pseudonymous IDs), which is
separate from the survey-key/session-DEK wrapping hierarchy.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from app.core.config import current_settings
from app.crypto._internal.errors import LinkageKeyError, LinkageKeyUnavailableError
from app.crypto._internal.models import SecretValue

if TYPE_CHECKING:
    from mypy_boto3_secretsmanager import SecretsManagerClient

logger = logging.getLogger(__name__)


def fetch_linkage_secret_from_aws(
    version_id: str | None = None,
    version_stage: str | None = None,
    *,
    client: SecretsManagerClient | None = None,
    secret_arn: str | None = None,
) -> SecretValue:
    """Fetch a linkage secret from AWS Secrets Manager."""
    if client is None:
        from app.crypto._internal.client_extension import get_crypto_clients

        client = get_crypto_clients().secretsmanager
    if secret_arn is None:
        secret_arn = current_settings().flowform.encryption.linkage_secret_arn

    try:
        if version_id is not None and version_stage is not None:
            raise LinkageKeyError("Use either version_id or version_stage, not both.")

        if version_id is not None:
            response = client.get_secret_value(SecretId=secret_arn, VersionId=version_id)
        elif version_stage is not None:
            response = client.get_secret_value(SecretId=secret_arn, VersionStage=version_stage)
        else:
            response = client.get_secret_value(SecretId=secret_arn)
    except Exception as exc:
        logger.error("Secrets Manager fetch failed: %s", type(exc).__name__)
        raise LinkageKeyUnavailableError() from exc

    try:
        return SecretValue.model_validate(response)
    except ValidationError as exc:
        raise LinkageKeyError("Secret response missing required fields") from exc
