import logging
import types
from typing import Any

import pytest
from flask import Flask, g, make_response
from pytest import MonkeyPatch

from app.logging import request_logging


@pytest.fixture
def app() -> Flask:
    """Create a minimal Flask app with a simple /ping route for tests."""
    app = Flask(__name__)

    @app.route("/ping")
    def ping():  # type: ignore[unused-ignore]
        return "pong", 204

    return app


def test_log_request_includes_expected_extra(monkeypatch: MonkeyPatch):
    """log_request logs all expected fields and computed duration_ms."""
    # Prepare a fake request and response within an app context
    flask_app = Flask(__name__)
    with flask_app.test_request_context("/test-path", method="GET"):
        response = make_response("", 204)
        g.request_id = "req-123"

        calls: dict[str, Any] = {}

        def fake_get_client_ip() -> str:
            return "1.2.3.4"

        def fake_get_log_level(status_code: int) -> int:
            return logging.INFO

        def fake_log(level, msg, *args, **kwargs):
            calls["level"] = level
            calls["msg"] = msg
            calls["args"] = args
            calls["extra"] = kwargs.get("extra")

        logger_wrapper = types.SimpleNamespace(log=fake_log)

        monkeypatch.setattr(request_logging, "get_client_ip", fake_get_client_ip)
        monkeypatch.setattr(request_logging, "get_log_level", fake_get_log_level)
        monkeypatch.setattr(request_logging, "HTTP_LOGGER", logger_wrapper)

        request_logging.log_request(response, duration_seconds=0.5)

        extra = calls["extra"]  # type: ignore[assignment]
        assert calls["level"] == logging.INFO
        assert extra["request_id"] == "req-123"  # type: ignore[index]
        assert extra["method"] == "GET"  # type: ignore[index]
        assert extra["path"] == "/test-path"  # type: ignore[index]
        assert extra["status_code"] == 204  # type: ignore[index]
        assert extra["remote_addr"] == "1.2.3.4"  # type: ignore[index]
        # duration_ms is computed from duration_seconds
        assert extra["duration_ms"] == pytest.approx(500.0)  # type: ignore[index]


def test_log_request_omits_duration_when_not_provided(monkeypatch: MonkeyPatch):
    """log_request does not include duration_ms when no duration is given."""
    flask_app = Flask(__name__)
    with flask_app.test_request_context("/no-duration", method="POST"):
        response = make_response("", 200)
        g.request_id = "req-456"

        captured: dict[str, Any] = {}

        def fake_get_client_ip() -> str:
            return "5.6.7.8"

        def fake_get_log_level(status_code: int) -> int:
            return logging.DEBUG

        def fake_log(level, msg, *args, **kwargs):
            captured["level"] = level
            captured["extra"] = kwargs.get("extra")

        logger_wrapper = types.SimpleNamespace(log=fake_log)

        monkeypatch.setattr(request_logging, "get_client_ip", fake_get_client_ip)
        monkeypatch.setattr(request_logging, "get_log_level", fake_get_log_level)
        monkeypatch.setattr(request_logging, "HTTP_LOGGER", logger_wrapper)

        request_logging.log_request(response)

        extra = captured["extra"]  # type: ignore[assignment]
        assert captured["level"] == logging.DEBUG
        assert extra["request_id"] == "req-456"  # type: ignore[index]
        assert extra["method"] == "POST"  # type: ignore[index]
        assert extra["path"] == "/no-duration"  # type: ignore[index]
        assert extra["status_code"] == 200  # type: ignore[index]
        assert extra["remote_addr"] == "5.6.7.8"  # type: ignore[index]
        assert "duration_ms" not in extra  # type: ignore[operator]


def test_register_request_logging_adds_header_and_duration(app: Flask, monkeypatch: MonkeyPatch):
    """register_request_logging logs with a duration and sets X-Request-ID."""
    times = [1.0, 3.5]

    def fake_perf_counter() -> float:
        return times.pop(0)

    monkeypatch.setattr(request_logging.time, "perf_counter", fake_perf_counter)

    captured: dict[str, object] = {}

    def fake_log_request(response, duration_seconds):
        captured["status_code"] = response.status_code
        captured["duration_seconds"] = duration_seconds

    monkeypatch.setattr(request_logging, "log_request", fake_log_request)

    request_logging.register_request_logging(app, include_duration=True)

    with app.test_client() as client:
        response = client.get("/ping")

    assert response.status_code == 204
    assert response.headers.get("X-Request-ID")
    assert captured["status_code"] == 204
    assert captured["duration_seconds"] == pytest.approx(2.5)


def test_register_request_logging_idempotent(app):
    """register_request_logging can be called multiple times without side effects."""
    # First registration should set the extension flag
    request_logging.register_request_logging(app, include_duration=False)
    assert app.extensions.get("request_logging_registered") is True

    # Second registration should be a no-op and not raise
    request_logging.register_request_logging(app, include_duration=True)
    assert app.extensions.get("request_logging_registered") is True
