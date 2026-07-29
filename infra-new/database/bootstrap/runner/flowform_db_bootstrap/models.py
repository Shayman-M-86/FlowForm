# TODO(migration): Update paths, contracts, and runtime wiring for infra-new before this file is used.
"""Typed inputs and database definitions for PostgreSQL bootstrap."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Self

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class BootstrapPhase(StrEnum):
    """Sanitized phase names suitable for operational logs."""

    INPUT = "input"
    LOAD_SECRET = "load_secret"
    CONNECT = "connect"
    METADATA_CHECK = "metadata_check"
    ROLES = "roles"
    DATABASES = "databases"
    DATABASE_CONFIGURATION = "database_configuration"
    VERIFICATION = "verification"
    RECORD_VERSION = "record_version"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class BootstrapRequest:
    """Validated reconciliation identity supplied by the operator."""

    version: str
    checksum: str

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> Self:
        version = str(event.get("BootstrapVersion", "")).strip()
        checksum = str(event.get("BootstrapChecksum", "")).strip()
        if not version.isdecimal():
            raise ValueError("Bootstrap version must be a positive integer.")
        if not SHA256_PATTERN.fullmatch(checksum):
            raise ValueError("Bootstrap checksum must be a lowercase SHA-256 digest.")
        return cls(version=version, checksum=checksum)

    def require_expected(self, *, version: str, checksum: str) -> None:
        """Reject an invocation that does not identify the deployed package."""
        if self.version != version or self.checksum != checksum:
            raise ValueError("Bootstrap request does not match the deployed package.")


@dataclass(frozen=True, slots=True)
class DatabaseCredentials:
    """Required fields from the RDS-managed master secret."""

    username: str
    password: str
    host: str
    port: int

    @classmethod
    def from_secret_string(
        cls,
        secret_string: str,
        *,
        host: str,
        port: int,
    ) -> Self:
        value = json.loads(secret_string)
        required = ("username", "password")
        missing = [name for name in required if name not in value]
        if missing:
            raise ValueError("The RDS master secret is missing required fields.")
        if not host or port < 1 or port > 65535:
            raise ValueError("The RDS endpoint configuration is invalid.")
        return cls(
            username=str(value["username"]),
            password=str(value["password"]),
            host=host,
            port=port,
        )


@dataclass(frozen=True, slots=True)
class DatabaseDefinition:
    """Names and SQL belonging to one logical application database."""

    name: str
    schema_name: str
    application_role: str
    setup_script: str
    schema_script: str


DATABASES = (
    DatabaseDefinition(
        name="flowform_core",
        schema_name="core_app",
        application_role="flowform_core_app",
        setup_script="core_database_v1.sql",
        schema_script="flowform_core_db_schema_v4.sql",
    ),
    DatabaseDefinition(
        name="flowform_response",
        schema_name="response_app",
        application_role="flowform_response_app",
        setup_script="response_database_v1.sql",
        schema_script="flowform_response_db_schema_v4.sql",
    ),
)
