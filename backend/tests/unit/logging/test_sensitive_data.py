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
    "aws_access_key": "FLOWFORM_TEST_AWS_ACCESS_KEY_5a96e",
    "aws_secret_key": "FLOWFORM_TEST_AWS_SECRET_KEY_244ad",
    "aws_session_token": "FLOWFORM_TEST_AWS_SESSION_TOKEN_014b8",
    "bearer": "FLOWFORM_TEST_BEARER_8bd22",
    "cookie": "FLOWFORM_TEST_SESSION_COOKIE_1de54",
    "database": "FLOWFORM_TEST_DB_PASSWORD_7ad91",
    "linkage": "FLOWFORM_TEST_LINKAGE_SECRET_3fc43",
    "provider_body": "FLOWFORM_TEST_PROVIDER_BODY_c1387",
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
                "redaction-canary-event database=%s authorization=Bearer %s Cookie: session=%s "
                "AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s AWS_SESSION_TOKEN=%s "
                "provider_message=%s aws_response=%s",
                f"postgresql://flowform:{_CANARIES['database']}@postgres-core/flowform",
                _CANARIES["bearer"],
                _CANARIES["cookie"],
                _CANARIES["aws_access_key"],
                _CANARIES["aws_secret_key"],
                _CANARIES["aws_session_token"],
                _CANARIES["provider_body"],
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
                        "aws_response": {
                            "Credentials": {
                                "AccessKeyId": _CANARIES["aws_access_key"],
                                "SecretAccessKey": _CANARIES["aws_secret_key"],
                                "SessionToken": _CANARIES["aws_session_token"],
                            },
                            "safe_field": "safe-aws-context",
                        },
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
        assert payload["metadata"]["aws_response"]["safe_field"] == "safe-aws-context"


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


def test_pytest_capture_never_retains_raw_secret_values(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("app.tests.redaction.pytest_capture")
    protect_root_handlers()

    with caplog.at_level(logging.INFO, logger=logger.name):
        logger.info(
            "pytest-capture-canary authorization=Bearer %s",
            _CANARIES["bearer"],
            extra={"metadata": {"client_secret": _CANARIES["linkage"]}},
        )

    assert caplog.records
    assert "pytest-capture-canary" in caplog.text
    assert REDACTED in caplog.text

    for canary in _CANARIES.values():
        assert canary not in caplog.text
        assert all(canary not in record.getMessage() for record in caplog.records)
        assert all(canary not in str(record.__dict__) for record in caplog.records)


def test_dangerous_dependency_debug_loggers_default_to_warning() -> None:
    configure_third_party_loggers()

    for logger_name, expected_level in THIRD_PARTY_LOG_LEVELS.items():
        assert logging.getLogger(logger_name).getEffectiveLevel() >= expected_level
