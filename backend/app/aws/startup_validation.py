"""Fail-closed startup probes for AWS services required by backend crypto."""

from __future__ import annotations

import hmac
import logging
import secrets
from typing import TYPE_CHECKING

from app.core.config import Settings
from app.core.errors import InitializationError

if TYPE_CHECKING:
    from app.aws.client_extension import AwsClients

logger = logging.getLogger(__name__)

_PROBE_PLAINTEXT_BYTES = 32


def validate_aws_runtime_access(*, settings: Settings, clients: AwsClients) -> None:
    """Prove dev/prod can read linkage material and use the configured KMS key."""
    environment = settings.flowform.env
    if environment == "test":
        return

    encryption = settings.flowform.encryption
    _validate_secrets_manager_access(
        clients=clients,
        secret_arn=encryption.linkage_secret_arn,
    )
    _validate_kms_access(
        clients=clients,
        key_arn=encryption.kms_key_arn,
        environment=environment,
    )
    logger.info("AWS startup validation succeeded for Secrets Manager and KMS")


def _validate_secrets_manager_access(*, clients: AwsClients, secret_arn: str) -> None:
    try:
        response = clients.secretsmanager.get_secret_value(
            SecretId=secret_arn,
            VersionStage="AWSCURRENT",
        )
        if not response.get("SecretString"):
            raise ValueError("Linkage secret has no SecretString")
    except Exception as exc:
        logger.error("AWS Secrets Manager startup validation failed: %s", type(exc).__name__)
        raise InitializationError(
            "AWS startup validation failed: unable to read the configured linkage secret from Secrets Manager."
        ) from exc


def _validate_kms_access(*, clients: AwsClients, key_arn: str, environment: str) -> None:
    plaintext = secrets.token_bytes(_PROBE_PLAINTEXT_BYTES)
    encryption_context = {
        "flowform_purpose": "startup_validation",
        "flowform_environment": environment,
    }

    try:
        encrypted = clients.kms.encrypt(
            KeyId=key_arn,
            Plaintext=plaintext,
            EncryptionContext=encryption_context,
        )
        ciphertext = encrypted.get("CiphertextBlob")
        if not ciphertext:
            raise ValueError("KMS encrypt response has no CiphertextBlob")

        decrypted = clients.kms.decrypt(
            KeyId=key_arn,
            CiphertextBlob=ciphertext,
            EncryptionContext=encryption_context,
        )
        recovered = decrypted.get("Plaintext")
        if recovered is None or not hmac.compare_digest(plaintext, recovered):
            raise ValueError("KMS startup round trip did not recover the probe value")
    except Exception as exc:
        logger.error("AWS KMS startup validation failed: %s", type(exc).__name__)
        raise InitializationError(
            "AWS startup validation failed: unable to encrypt and decrypt with the configured KMS key."
        ) from exc
