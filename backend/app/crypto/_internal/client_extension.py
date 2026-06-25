# app/crypto/_internal/client_extension.py

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast, overload

import boto3
from botocore.config import Config
from flask import Flask, current_app
from pydantic import SecretStr

from app.core.config import Settings

if TYPE_CHECKING:
    from mypy_boto3_kms import KMSClient
    from mypy_boto3_secretsmanager import SecretsManagerClient


EXTENSION_KEY = "crypto_clients"

_CLIENT_CONFIG = Config(tcp_keepalive=True)


@dataclass(frozen=True, slots=True)
class CryptoClients:
    """Holds AWS clients used by crypto services."""

    kms: KMSClient
    secretsmanager: SecretsManagerClient


class CryptoClientManager:
    """Owns AWS clients used by crypto services."""

    def __init__(self) -> None:
        self._clients: CryptoClients | None = None

    def init_app(self, app: Flask) -> None:
        settings: Settings = app.extensions["settings"]
        encryption = settings.flowform.encryption

        self._clients = CryptoClients(
            kms=self._build_client(
                "kms",
                region=encryption.aws_region,
                access_key_id=encryption.aws_access_key_id,
                secret_access_key=encryption.aws_secret_access_key,
            ),
            secretsmanager=self._build_client(
                "secretsmanager",
                region=encryption.aws_region,
                access_key_id=encryption.aws_access_key_id,
                secret_access_key=encryption.aws_secret_access_key,
            ),
        )

        app.extensions[EXTENSION_KEY] = self

    @property
    def kms(self) -> KMSClient:
        return self.clients.kms

    @property
    def secretsmanager(self) -> SecretsManagerClient:
        return self.clients.secretsmanager

    @property
    def clients(self) -> CryptoClients:
        if self._clients is None:
            raise RuntimeError("Crypto clients are not initialized.")
        return self._clients

    @overload
    def _build_client(
        self, service_name: Literal["kms"], *, region: str, access_key_id: SecretStr, secret_access_key: SecretStr
    ) -> KMSClient: ...

    @overload
    def _build_client(
        self,
        service_name: Literal["secretsmanager"],
        *,
        region: str,
        access_key_id: SecretStr,
        secret_access_key: SecretStr,
    ) -> SecretsManagerClient: ...

    def _build_client(
        self,
        service_name: Literal["kms", "secretsmanager"],
        *,
        region: str,
        access_key_id: SecretStr,
        secret_access_key: SecretStr,
    ) -> KMSClient | SecretsManagerClient:
        session = boto3.Session(
            region_name=region,
            aws_access_key_id=access_key_id.get_secret_value(),
            aws_secret_access_key=secret_access_key.get_secret_value(),
        )

        client = session.client(service_name, config=_CLIENT_CONFIG)

        if service_name == "kms":
            return cast("KMSClient", client)

        return cast("SecretsManagerClient", client)


def get_crypto_client_manager() -> CryptoClientManager:
    manager = current_app.extensions.get(EXTENSION_KEY)

    if manager is None:
        raise RuntimeError("Crypto clients are not initialized.")

    return cast(CryptoClientManager, manager)


def get_crypto_clients() -> CryptoClients:
    return get_crypto_client_manager().clients
