from __future__ import annotations

import logging
import types
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from flask import Flask, Response, g, make_response

from app.logging import request_logging


@pytest.fixture(scope="module")
def request_context_app() -> Flask:
    """Shared Flask app for request-context-only tests."""
    return Flask(__name__)


@pytest.fixture
def app() -> Flask:
    """Fresh Flask app for tests that register hooks/extensions."""
    flask_app = Flask(__name__)

    @flask_app.get("/ping")
    def ping() -> tuple[str, int]:
        return "", 204

    return flask_app


@pytest.fixture
def captured_log() -> dict[str, Any]:
    """Capture logger calls for assertions."""
    return {}


@pytest.fixture
def patch_request_logging(
    monkeypatch: pytest.MonkeyPatch,
    captured_log: dict[str, Any],
) -> Callable[..., None]:
    """Patch request_logging dependencies for a single test."""

    def _patch(*, ip: str, level: int) -> None:
        def fake_get_client_ip() -> str:
            return ip

        def fake_get_log_level(status_code: int) -> int:
            return level

        def fake_log(log_level: int, msg: str, *args: Any, **kwargs: Any) -> None:
            captured_log["level"] = log_level
            captured_log["msg"] = msg
            captured_log["args"] = args
            captured_log["extra"] = kwargs.get("extra")

        monkeypatch.setattr(request_logging, "get_client_ip", fake_get_client_ip)
        monkeypatch.setattr(request_logging, "get_log_level", fake_get_log_level)
        monkeypatch.setattr(
            request_logging,
            "HTTP_LOGGER",
            types.SimpleNamespace(log=fake_log),
        )

    return _patch


@pytest.fixture
def request_response(
    request_context_app: Flask,
) -> Callable[..., Any]:
    """Build a response inside a request context for a single test."""

    @contextmanager
    def _request_response(
        *,
        path: str,
        method: str,
        request_id: str,
        status_code: int,
    ) -> Iterator[Response]:
        with request_context_app.test_request_context(path, method=method):
            g.request_id = request_id
            yield make_response("", status_code)

    return _request_response


def test_log_request_includes_expected_extra(
    patch_request_logging: Callable[..., None],
    captured_log: dict[str, Any],
    request_response: Callable[..., Any],
) -> None:
    """log_request logs all expected fields and computed duration_ms."""
    patch_request_logging(ip="1.2.3.4", level=logging.INFO)

    with request_response(
        path="/test-path",
        method="GET",
        request_id="req-123",
        status_code=204,
    ) as response:
        request_logging.log_request(response, duration_seconds=0.5)

    extra = captured_log["extra"]
    assert captured_log["level"] == logging.INFO
    assert extra["request_id"] == "req-123"
    assert extra["method"] == "GET"
    assert extra["path"] == "/test-path"
    assert extra["status_code"] == 204
    assert extra["remote_addr"] == "1.2.3.4"
    assert extra["duration_ms"] == pytest.approx(500.0)


def test_log_request_omits_duration_when_not_provided(
    patch_request_logging: Callable[..., None],
    captured_log: dict[str, Any],
    request_response: Callable[..., Any],
) -> None:
    """log_request does not include duration_ms when no duration is given."""
    patch_request_logging(ip="5.6.7.8", level=logging.DEBUG)

    with request_response(
        path="/no-duration",
        method="POST",
        request_id="req-456",
        status_code=200,
    ) as response:
        request_logging.log_request(response)

    extra = captured_log["extra"]
    assert captured_log["level"] == logging.DEBUG
    assert extra["request_id"] == "req-456"
    assert extra["method"] == "POST"
    assert extra["path"] == "/no-duration"
    assert extra["status_code"] == 200
    assert extra["remote_addr"] == "5.6.7.8"
    assert "duration_ms" not in extra


def test_register_request_logging_adds_header_and_duration(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """register_request_logging logs with a duration and sets X-Request-ID."""
    times = [1.0, 3.5]

    def fake_perf_counter() -> float:
        return times.pop(0)

    captured: dict[str, object] = {}

    def fake_log_request(response: Response, duration_seconds: float | None) -> None:
        captured["status_code"] = response.status_code
        captured["duration_seconds"] = duration_seconds

    monkeypatch.setattr(request_logging.time, "perf_counter", fake_perf_counter)
    monkeypatch.setattr(request_logging, "log_request", fake_log_request)

    request_logging.register_request_logging(app, include_duration=True)

    with app.test_client() as client:
        response = client.get("/ping")

    assert response.status_code == 204
    assert response.headers.get("X-Request-ID")
    assert captured["status_code"] == 204
    assert captured["duration_seconds"] == pytest.approx(2.5)


def test_register_request_logging_idempotent(app: Flask) -> None:
    """register_request_logging can be called multiple times without side effects."""
    request_logging.register_request_logging(app, include_duration=False)
    assert app.extensions.get("request_logging_registered") is True

    request_logging.register_request_logging(app, include_duration=True)
    assert app.extensions.get("request_logging_registered") is True
