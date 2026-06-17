"""Secrets Manager access for the linkage secret."""

from __future__ import annotations

import base64
import logging
from typing import Any

import boto3
from pydantic import SecretStr

logger = logging.getLogger(__name__)


class LinkageSecretError(Exception):
    """Raised when fetching the linkage secret from Secrets Manager fails."""


def _build_secretsmanager_client(
    region: str,
    access_key_id: SecretStr,
    secret_access_key: SecretStr,
) -> Any:
    session = boto3.Session(
        region_name=region,
        aws_access_key_id=access_key_id.get_secret_value(),
        aws_secret_access_key=secret_access_key.get_secret_value(),
    )
    return session.client("secretsmanager")


def get_linkage_secret(
    secret_arn: str,
    version_id: str | None = None,
    *,
    region: str,
    access_key_id: SecretStr,
    secret_access_key: SecretStr,
) -> bytes:
    """Fetch the linkage secret from Secrets Manager and return raw bytes."""
    client = _build_secretsmanager_client(region, access_key_id, secret_access_key)
    kwargs: dict[str, Any] = {"SecretId": secret_arn}
    if version_id is not None:
        kwargs["VersionId"] = version_id
    try:
        response = client.get_secret_value(**kwargs)
    except Exception as exc:
        logger.error(
            "Secrets Manager fetch failed for secret: %s",
            type(exc).__name__,
        )
        raise LinkageSecretError("Failed to fetch linkage secret") from exc
    secret_string = response.get("SecretString")
    if secret_string is not None:
        return base64.b64decode(secret_string)
    return response["SecretBinary"]
