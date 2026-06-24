"""Secrets Manager access for linkage secrets."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config
from pydantic import SecretStr

from app.crypto.errors import LinkageKeyError, LinkageSecretError

_CLIENT_CONFIG = Config(tcp_keepalive=True)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SecretValue:
    """A secret string and its AWS-assigned version identifier."""

    secret_string: str
    version_id: str


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
    return session.client("secretsmanager", config=_CLIENT_CONFIG)


def get_linkage_secret(
    secret_arn: str,
    version_id: str | None = None,
    version_stage: str | None = None,
    *,
    region: str,
    access_key_id: SecretStr,
    secret_access_key: SecretStr,
    client: Any | None = None,
) -> SecretValue:
    """Fetch a secret from Secrets Manager.

    Returns the SecretString content and the AWS VersionId. Raises
    ``LinkageSecretError`` on any AWS failure and ``LinkageKeyError``
    when the secret has no string value.
    """
    secrets_client = client or _build_secretsmanager_client(
        region,
        access_key_id,
        secret_access_key,
    )
    kwargs: dict[str, Any] = {"SecretId": secret_arn}
    if version_id is not None:
        kwargs["VersionId"] = version_id
    if version_stage is not None:
        kwargs["VersionStage"] = version_stage
    try:
        response = secrets_client.get_secret_value(**kwargs)
    except Exception as exc:
        logger.error("Secrets Manager fetch failed: %s", type(exc).__name__)
        raise LinkageSecretError("Failed to fetch linkage secret") from exc

    secret_string = response.get("SecretString")
    if secret_string is None:
        raise LinkageKeyError("Secret does not contain a string value")
    return SecretValue(
        secret_string=secret_string,
        version_id=response["VersionId"],
    )
