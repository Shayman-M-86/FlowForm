from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast, overload

import boto3
from botocore.config import Config
from flask import Flask, current_app

from app.core.config import AwsSettings, Settings

if TYPE_CHECKING:
    from mypy_boto3_kms import KMSClient
    from mypy_boto3_secretsmanager import SecretsManagerClient
    from mypy_boto3_sesv2 import SESV2Client


EXTENSION_KEY = "aws_clients"

_CLIENT_CONFIG = Config(tcp_keepalive=True)


@dataclass(frozen=True, slots=True)
class AwsClients:
    """Holds shared AWS clients used by application services."""

    kms: KMSClient
    secretsmanager: SecretsManagerClient
    sesv2: SESV2Client


class AwsClientManager:
    """Owns shared AWS clients for the Flask application."""

    def __init__(self) -> None:
        self._clients: AwsClients | None = None

    def init_app(self, app: Flask) -> None:
        """Initialise AWS clients and attach this manager to Flask."""
        settings: Settings = app.extensions["settings"]
        aws = settings.flowform.aws

        self._clients = AwsClients(
            kms=self._build_client("kms", aws=aws),
            secretsmanager=self._build_client("secretsmanager", aws=aws),
            sesv2=self._build_client("sesv2", aws=aws),
        )

        app.extensions[EXTENSION_KEY] = self

    @property
    def clients(self) -> AwsClients:
        if self._clients is None:
            raise RuntimeError("AWS clients are not initialized.")

        return self._clients

    @property
    def kms(self) -> KMSClient:
        return self.clients.kms

    @property
    def secretsmanager(self) -> SecretsManagerClient:
        return self.clients.secretsmanager

    @property
    def sesv2(self) -> SESV2Client:
        return self.clients.sesv2

    @overload
    def _build_client(
        self,
        service_name: Literal["kms"],
        *,
        aws: AwsSettings,
    ) -> KMSClient: ...

    @overload
    def _build_client(
        self,
        service_name: Literal["secretsmanager"],
        *,
        aws: AwsSettings,
    ) -> SecretsManagerClient: ...

    @overload
    def _build_client(
        self,
        service_name: Literal["sesv2"],
        *,
        aws: AwsSettings,
    ) -> SESV2Client: ...

    def _build_client(
        self,
        service_name: Literal["kms", "secretsmanager", "sesv2"],
        *,
        aws: AwsSettings,
    ) -> KMSClient | SecretsManagerClient | SESV2Client:
        """Build a typed boto3 client using shared AWS settings."""
        if aws.access_key_id is not None and aws.secret_access_key is not None:
            session = boto3.Session(
                region_name=aws.region,
                aws_access_key_id=aws.access_key_id.get_secret_value(),
                aws_secret_access_key=aws.secret_access_key.get_secret_value(),
            )
        else:
            session = boto3.Session(
                region_name=aws.region,
            )

        client = session.client(service_name, config=_CLIENT_CONFIG)

        if service_name == "kms":
            return cast("KMSClient", client)

        if service_name == "secretsmanager":
            return cast("SecretsManagerClient", client)

        return cast("SESV2Client", client)


def get_aws_client_manager(app: Flask | None = None) -> AwsClientManager:
    """Return the AWS client manager from Flask extensions."""
    extensions = app.extensions if app is not None else current_app.extensions
    manager = extensions.get(EXTENSION_KEY)

    if manager is None:
        raise RuntimeError("AWS clients are not initialized.")

    return cast(AwsClientManager, manager)


def get_aws_clients(app: Flask | None = None) -> AwsClients:
    """Return shared AWS clients."""
    return get_aws_client_manager(app).clients