"""External service adapters for PostgreSQL bootstrap."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

import psycopg
from psycopg import Connection

from .models import DatabaseCredentials

SQL_DIR = Path(__file__).with_name("sql")
SCHEMA_DIR = Path(__file__).with_name("schema")
CONNECT_ATTEMPTS = 8
TABLE_NAME_PATTERN = re.compile(
    r"^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r'"?([a-z_][a-z0-9_]*)"?\s*\(',
    re.IGNORECASE | re.MULTILINE,
)


class SqlRepository:
    """Loads packaged, versioned SQL assets."""

    def __init__(
        self,
        root: Path = SQL_DIR,
        schema_root: Path = SCHEMA_DIR,
    ) -> None:
        self._root = root
        self._schema_root = schema_root

    def read(self, filename: str) -> str:
        return (self._root / filename).read_text(encoding="utf-8")

    def read_schema(self, filename: str) -> str:
        return (self._schema_root / filename).read_text(encoding="utf-8")

    def schema_table_names(self, filename: str) -> frozenset[str]:
        schema_sql = self.read_schema(filename)
        table_names = frozenset(TABLE_NAME_PATTERN.findall(schema_sql))
        if not table_names:
            raise ValueError("The packaged application schema contains no tables.")
        return table_names


class SecretsManagerCredentialProvider:
    """Retrieves exactly one RDS-managed credential."""

    def __init__(
        self,
        client: Any,
        secret_arn: str,
        *,
        host: str,
        port: int,
    ) -> None:
        self._client = client
        self._secret_arn = secret_arn
        self._host = host
        self._port = port

    def load(self) -> DatabaseCredentials:
        response = self._client.get_secret_value(SecretId=self._secret_arn)
        secret_string = response.get("SecretString")
        if not secret_string:
            raise ValueError("The RDS master secret has no SecretString value.")
        return DatabaseCredentials.from_secret_string(
            secret_string,
            host=self._host,
            port=self._port,
        )


class PostgresConnector:
    """Creates TLS PostgreSQL sessions with bounded connection retries."""

    def __init__(
        self,
        credentials: DatabaseCredentials,
        *,
        attempts: int = CONNECT_ATTEMPTS,
    ) -> None:
        self._credentials = credentials
        self._attempts = attempts

    def connect(
        self,
        database_name: str,
        *,
        autocommit: bool,
    ) -> Connection[Any]:
        for attempt in range(1, self._attempts + 1):
            try:
                connection = psycopg.connect(
                    host=self._credentials.host,
                    port=self._credentials.port,
                    dbname=database_name,
                    user=self._credentials.username,
                    password=self._credentials.password,
                    sslmode="require",
                    connect_timeout=8,
                    autocommit=autocommit,
                )
                self._configure_session(connection)
                return connection
            except psycopg.OperationalError:
                if attempt == self._attempts:
                    raise
                time.sleep(min(2**attempt, 20))

        raise RuntimeError("PostgreSQL connection retries were exhausted.")

    @staticmethod
    def _configure_session(connection: Connection[Any]) -> None:
        connection.execute("SET lock_timeout = '10s'")
        connection.execute("SET statement_timeout = '120s'")
        connection.execute("SET idle_in_transaction_session_timeout = '120s'")
