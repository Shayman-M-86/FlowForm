"""RDS IAM database authentication token support.

Under IAM auth the application holds no long-lived database password. Each
physical connection authenticates with a short-lived token (valid ~15 minutes)
signed locally from the instance's AWS credentials.

Because tokens expire while an engine is long-lived, the token cannot be baked
into the connection URL. It is injected per physical connection through
SQLAlchemy's ``do_connect`` hook, which leaves pooling, ``pool_recycle``,
``pool_pre_ping``, and overflow behaviour untouched.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import boto3
from sqlalchemy import Engine, event

from app.core.config import AwsSettings, DatabaseSettings
from app.core.errors import ConfigError

if TYPE_CHECKING:
    from mypy_boto3_rds import RDSClient

logger = logging.getLogger(__name__)

RDS_CA_BUNDLE_PATH = "/etc/ssl/certs/aws-rds-ap-southeast-2-bundle.pem"


class RdsIamTokenProvider:
    """Generates RDS IAM authentication tokens for a single database target.

    Token generation is a local signing operation against the caller's AWS
    credentials, not a network call to RDS, so it is cheap enough to run on
    each physical connection without caching.
    """

    def __init__(self, *, host: str, port: int, app_user: str, aws: AwsSettings) -> None:
        self._host = host
        self._port = port
        self._app_user = app_user
        self._client = self._build_client(aws)

    @staticmethod
    def _build_client(aws: AwsSettings) -> RDSClient:
        """Build an RDS client using the shared AWS settings."""
        if aws.access_key_id is not None and aws.secret_access_key is not None:
            session = boto3.Session(
                region_name=aws.region,
                aws_access_key_id=aws.access_key_id.get_secret_value(),
                aws_secret_access_key=aws.secret_access_key.get_secret_value(),
            )
        else:
            session = boto3.Session(region_name=aws.region)

        return session.client("rds")

    def generate_token(self) -> str:
        """Return a fresh IAM authentication token for this database target."""
        return self._client.generate_db_auth_token(
            DBHostname=self._host,
            Port=self._port,
            DBUsername=self._app_user,
        )


def attach_iam_auth(engine: Engine, *, database: DatabaseSettings, aws: AwsSettings) -> None:
    """Supply a freshly generated IAM token as the password for each connection.

    Raises:
        ConfigError: If the database target is missing the parts required to
            sign a token.
    """
    if database.host is None or database.app_user is None:
        raise ConfigError("Database host and app_user are required for IAM database authentication")

    provider = RdsIamTokenProvider(
        host=database.host,
        port=database.port,
        app_user=database.app_user,
        aws=aws,
    )

    @event.listens_for(engine, "do_connect")
    def _provide_iam_token(
        _dialect: Any,
        _conn_rec: Any,
        _cargs: Any,
        cparams: dict[str, Any],
    ) -> None:
        """Inject a short-lived IAM token at physical connection time."""
        cparams["password"] = provider.generate_token()
        # RDS IAM authentication is only accepted over TLS.
        cparams.setdefault("sslmode", "verify-full")
        cparams.setdefault("sslrootcert", RDS_CA_BUNDLE_PATH)

    logger.info(
        "RDS IAM database authentication enabled for %s@%s:%s",
        database.app_user,
        database.host,
        database.port,
    )
