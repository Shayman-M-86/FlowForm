"""Secrets Manager access for linkage secrets."""

from __future__ import annotations

import logging
from typing import Any

import boto3
from pydantic import SecretStr

from app.crypto.errors import LinkageKeyError, LinkageSecretError

logger = logging.getLogger(__name__)


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
) -> str:
    """Fetch a secret string from Secrets Manager.

    Returns the raw SecretString content. Raises ``LinkageSecretError`` on any
    AWS failure and ``LinkageKeyError`` when the secret has no string value.
    """
    client = _build_secretsmanager_client(region, access_key_id, secret_access_key)
    kwargs: dict[str, Any] = {"SecretId": secret_arn}
    if version_id is not None:
        kwargs["VersionId"] = version_id
    try:
        response = client.get_secret_value(**kwargs)
    except Exception as exc:
        logger.error("Secrets Manager fetch failed: %s", type(exc).__name__)
        raise LinkageSecretError("Failed to fetch linkage secret") from exc

    secret_string = response.get("SecretString")
    if secret_string is None:
        raise LinkageKeyError("Secret does not contain a string value")
    return secret_string
