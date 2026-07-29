"""AWS Lambda entry point for the private PostgreSQL bootstrap."""

from __future__ import annotations

import logging
import os
import re
import time
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

OPERATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
SUPPRESSED_ERROR_DETAIL = "detail suppressed"
SAFE_ERROR_PREFIXES = (
    "Operation ID is invalid.",
    "Bootstrap version must be a positive integer.",
    "Bootstrap checksum must be a lowercase SHA-256 digest.",
    "Bootstrap request does not match the deployed package.",
    "Bootstrap version already exists with a different checksum.",
    "The RDS master secret is missing required fields.",
    "The RDS master secret has no SecretString value.",
    "The RDS endpoint configuration is invalid.",
    "The packaged application schema contains no tables.",
    "Database schema is neither empty nor the expected baseline",
    "Cluster verification failed:",
    "Application table verification failed",
    "Application table ownership verification failed",
    "Database configuration verification failed",
    "Application table privilege verification failed",
    "Application sequence privilege verification failed",
    "PostgreSQL connection retries were exhausted.",
)


def _operation_id(event: dict[str, Any], lambda_request_id: str) -> str:
    """Return a bounded correlation identity suitable for operational logs."""
    value = event.get("OperationId")
    if value is None:
        return f"lambda-{lambda_request_id}"[:128]
    if not isinstance(value, str) or not OPERATION_ID_PATTERN.fullmatch(value):
        raise ValueError("Operation ID is invalid.")
    return value


def _safe_error_detail(exc: Exception) -> str:
    """Expose only messages created by this bootstrap package."""
    detail = str(exc)
    if any(detail.startswith(prefix) for prefix in SAFE_ERROR_PREFIXES):
        return detail[:500]
    return SUPPRESSED_ERROR_DETAIL


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Run bootstrap and return only a sanitized operator result."""
    started_at = time.monotonic()
    phase = BootstrapPhase.INPUT
    bootstrapper: PostgresBootstrapper | None = None
    request: BootstrapRequest | None = None
    operation_id = "unattributed"
    lambda_request_id = str(getattr(context, "aws_request_id", "unknown"))[:128]
    common_log_fields = {
        "component": "database-bootstrap",
        "environment": os.environ.get("FLOWFORM_ENVIRONMENT", "unknown"),
        "lambda_request_id": lambda_request_id,
    }
    try:
        operation_id = _operation_id(event, lambda_request_id)
        request = BootstrapRequest.from_event(event)
        request.require_expected(
            version=os.environ["BOOTSTRAP_VERSION"],
            checksum=os.environ["BOOTSTRAP_CHECKSUM"],
        )
        LOGGER.info(
            "database_bootstrap.started",
            extra={
                **common_log_fields,
                "operation_id": operation_id,
                "phase": phase.value,
                "outcome": "started",
                "bootstrap_version": request.version,
                "bootstrap_checksum": request.checksum,
            },
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
        LOGGER.info(
            "database_bootstrap.completed",
            extra={
                **common_log_fields,
                "operation_id": operation_id,
                "phase": BootstrapPhase.COMPLETE.value,
                "outcome": "succeeded",
                "duration_ms": round((time.monotonic() - started_at) * 1000),
                "bootstrap_version": request.version,
                "bootstrap_checksum": request.checksum,
            },
        )
        return {
            "Succeeded": True,
            "BootstrapVersion": request.version,
            "BootstrapChecksum": request.checksum,
        }
    except Exception as exc:
        if bootstrapper is not None:
            phase = bootstrapper.phase
        LOGGER.error(
            "database_bootstrap.failed",
            extra={
                **common_log_fields,
                "operation_id": operation_id,
                "phase": phase.value,
                "outcome": "failed",
                "duration_ms": round((time.monotonic() - started_at) * 1000),
                "bootstrap_version": (
                    request.version if request is not None else os.environ.get("BOOTSTRAP_VERSION", "unknown")
                ),
                "bootstrap_checksum": (
                    request.checksum if request is not None else os.environ.get("BOOTSTRAP_CHECKSUM", "unknown")
                ),
                "error_code": type(exc).__name__[:120],
                "error_detail": _safe_error_detail(exc),
            },
        )
        return {
            "Succeeded": False,
            "ErrorCode": type(exc).__name__[:120],
            "ErrorMessage": f"Database bootstrap failed during {phase.value}."[:800],
        }
