from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.aws import get_aws_clients

if TYPE_CHECKING:
    from mypy_boto3_kms import KMSClient
    from mypy_boto3_secretsmanager import SecretsManagerClient


@dataclass(frozen=True, slots=True)
class CryptoClients:
    """Holds AWS clients used by crypto services."""

    kms: KMSClient
    secretsmanager: SecretsManagerClient


def get_crypto_clients() -> CryptoClients:
    """Return AWS clients required by crypto services."""
    aws_clients = get_aws_clients()

    return CryptoClients(
        kms=aws_clients.kms,
        secretsmanager=aws_clients.secretsmanager,
    )