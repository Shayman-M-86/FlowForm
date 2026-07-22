from __future__ import annotations

import io
import json
import logging

import pytest

from app.logging.logging_config import (
    THIRD_PARTY_LOG_LEVELS,
    build_stream_handler,
    configure_third_party_loggers,
)
from app.logging.sensitive_data import REDACTED, SensitiveDataFilter, protect_root_handlers

_CANARIES = {
    "bearer": "FLOWFORM_TEST_BEARER_8bd22",
    "cookie": "FLOWFORM_TEST_SESSION_COOKIE_1de54",
    "database": "FLOWFORM_TEST_DB_PASSWORD_7ad91",
    "linkage": "FLOWFORM_TEST_LINKAGE_SECRET_3fc43",
}


@pytest.mark.parametrize("json_logs", [False, True])
def test_handler_output_redacts_sensitive_values_without_dropping_context(json_logs: bool) -> None:
    output = io.StringIO()
    handler = build_stream_handler(json_logs=json_logs, stream=output)
    logger = logging.getLogger(f"app.tests.redaction.{json_logs}")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    try:
        try:
            raise RuntimeError(f"client_secret={_CANARIES['linkage']}")
        except RuntimeError:
            logger.exception(
                "redaction-canary-event database=%s authorization=Bearer %s Cookie: session=%s aws_response=%s",
                f"postgresql://flowform:{_CANARIES['database']}@postgres-core/flowform",
                _CANARIES["bearer"],
                _CANARIES["cookie"],
                {
                    "SecretString": _CANARIES["linkage"],
                    "VersionId": "safe-version",
                },
                extra={
                    "metadata": {
                        "password": _CANARIES["database"],
                        "nested": [
                            {"secret_string": _CANARIES["linkage"]},
                            {"safe_field": "safe-context"},
                        ],
                    }
                },
            )
    finally:
        handler.flush()
        handler.close()
        logger.handlers = []

    rendered = output.getvalue()
    for canary in _CANARIES.values():
        assert canary not in rendered

    assert "redaction-canary-event" in rendered
    assert "safe-version" in rendered
    assert "RuntimeError" in rendered
    assert REDACTED in rendered

    if json_logs:
        payload = json.loads(rendered)
        assert payload["metadata"]["nested"][1]["safe_field"] == "safe-context"


def test_stream_handlers_are_protected_at_construction() -> None:
    handler = build_stream_handler(json_logs=False, stream=io.StringIO())
    try:
        assert any(isinstance(item, SensitiveDataFilter) for item in handler.filters)
    finally:
        handler.close()


def test_existing_root_handlers_receive_redaction_filter() -> None:
    root = logging.getLogger()
    handler = logging.StreamHandler(io.StringIO())
    root.addHandler(handler)
    try:
        protect_root_handlers()
        assert any(isinstance(item, SensitiveDataFilter) for item in handler.filters)
    finally:
        root.removeHandler(handler)
        handler.close()


def test_dangerous_dependency_debug_loggers_default_to_warning() -> None:
    configure_third_party_loggers()

    for logger_name, expected_level in THIRD_PARTY_LOG_LEVELS.items():
        assert logging.getLogger(logger_name).getEffectiveLevel() >= expected_level
