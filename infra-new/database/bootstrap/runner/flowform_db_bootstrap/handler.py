# TODO(migration): Update paths, contracts, and runtime wiring for infra-new before this file is used.
"""AWS Lambda entry point for the private PostgreSQL bootstrap."""

from __future__ import annotations

import logging
import os
from typing import Any

import boto3

from .models import BootstrapPhase, BootstrapRequest
from .postgres import PostgresBootstrapper
from .services import (
    PostgresConnector,
    SecretsManagerCredentialProvider,
    SqlRepository,
)

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Run bootstrap and return only a sanitized operator result."""
    phase = BootstrapPhase.INPUT
    bootstrapper: PostgresBootstrapper | None = None
    try:
        request = BootstrapRequest.from_event(event)
        request.require_expected(
            version=os.environ["BOOTSTRAP_VERSION"],
            checksum=os.environ["BOOTSTRAP_CHECKSUM"],
        )
        phase = BootstrapPhase.LOAD_SECRET
        credentials = SecretsManagerCredentialProvider(
            boto3.client("secretsmanager"),
            os.environ["DATABASE_SECRET_ARN"],
            host=os.environ["DATABASE_HOST"],
            port=int(os.environ["DATABASE_PORT"]),
        ).load()
        bootstrapper = PostgresBootstrapper(
            connector=PostgresConnector(credentials),
            scripts=SqlRepository(),
        )
        bootstrapper.run(request)
        LOGGER.info("Database bootstrap and verification completed.")
        return {
            "Succeeded": True,
            "BootstrapVersion": request.version,
            "BootstrapChecksum": request.checksum,
        }
    except Exception as exc:
        if bootstrapper is not None:
            phase = bootstrapper.phase
        failure_detail = str(exc) if isinstance(exc, RuntimeError) else "detail suppressed"
        LOGGER.error(
            "Database bootstrap failed during phase %s with error type %s: %s.",
            phase.value,
            type(exc).__name__,
            failure_detail,
        )
        return {
            "Succeeded": False,
            "ErrorCode": type(exc).__name__[:120],
            "ErrorMessage": f"Database bootstrap failed during {phase.value}."[:800],
        }
