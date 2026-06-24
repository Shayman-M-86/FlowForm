"""KMS wrap/unwrap for envelope key material."""

from __future__ import annotations

import logging
from typing import Any

import boto3
from pydantic import SecretStr

from app.crypto.errors import KmsError

logger = logging.getLogger(__name__)


def _build_kms_client(
    region: str,
    access_key_id: SecretStr,
    secret_access_key: SecretStr,
) -> Any:
    session = boto3.Session(
        region_name=region,
        aws_access_key_id=access_key_id.get_secret_value(),
        aws_secret_access_key=secret_access_key.get_secret_value(),
    )
    return session.client("kms")


def wrap_dek(
    plaintext_dek: bytes,
    key_arn: str,
    context: dict[str, str],
    *,
    region: str,
    access_key_id: SecretStr,
    secret_access_key: SecretStr,
) -> bytes:
    """Encrypt a plaintext DEK using KMS. Returns the wrapped (ciphertext) blob."""
    client = _build_kms_client(region, access_key_id, secret_access_key)
    try:
        response = client.encrypt(
            KeyId=key_arn,
            Plaintext=plaintext_dek,
            EncryptionContext=context,
        )
    except Exception as exc:
        logger.error("KMS encrypt failed for key_arn=%s: %s", key_arn, type(exc).__name__)
        raise KmsError("KMS encrypt failed") from exc
    return response["CiphertextBlob"]


def unwrap_dek(
    wrapped_dek: bytes,
    key_arn: str,
    context: dict[str, str],
    *,
    region: str,
    access_key_id: SecretStr,
    secret_access_key: SecretStr,
) -> bytes:
    """Decrypt a wrapped DEK using KMS. Returns the plaintext DEK."""
    client = _build_kms_client(region, access_key_id, secret_access_key)
    try:
        response = client.decrypt(
            KeyId=key_arn,
            CiphertextBlob=wrapped_dek,
            EncryptionContext=context,
        )
    except Exception as exc:
        logger.error("KMS decrypt failed for key_arn=%s: %s", key_arn, type(exc).__name__)
        raise KmsError("KMS decrypt failed") from exc
    return response["Plaintext"]
