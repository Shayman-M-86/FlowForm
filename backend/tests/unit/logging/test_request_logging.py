from __future__ import annotations

import logging
import types
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import pytest  # type: ignore[import]
from flask import Flask, Response, g, make_response, request

from app.logging import request_logging
from app.utils.general import get_log_level


@pytest.mark.parametrize(
    ("status_code", "expected_level"),
    [
        (200, logging.INFO),
        (204, logging.INFO),
        (302, logging.INFO),
        (404, logging.WARNING),
        (422, logging.WARNING),
        (500, logging.ERROR),
        (503, logging.ERROR),
    ],
)
def test_get_log_level_maps_status_to_level(status_code: int, expected_level: int) -> None:
    # 2xx/3xx log at INFO so completed requests surface at the INFO root level in
    # every environment (previously 2xx was DEBUG and vanished under gunicorn).
    assert get_log_level(status_code) == expected_level


_VALID_UUID = "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def resolver_app() -> Flask:
    """Minimal app for exercising _resolve_request_id in a request context."""
    return Flask(__name__)


def test_resolve_request_id_adopts_valid_inbound_header(resolver_app: Flask) -> None:
    with resolver_app.test_request_context(headers={"X-Request-ID": _VALID_UUID}):
        assert request_logging._resolve_request_id() == _VALID_UUID


def test_resolve_request_id_normalises_uppercase_uuid(resolver_app: Flask) -> None:
    # A valid-but-noncanonical UUID is re-rendered by us, never echoed verbatim.
    with resolver_app.test_request_context(headers={"X-Request-ID": _VALID_UUID.upper()}):
        assert request_logging._resolve_request_id() == _VALID_UUID


def test_resolve_request_id_mints_when_header_absent(resolver_app: Flask) -> None:
    with resolver_app.test_request_context():
        resolved = request_logging._resolve_request_id()
    uuid.UUID(resolved)  # a fresh, well-formed UUID


@pytest.mark.parametrize(
    "bad_value",
    [
        "not-a-uuid",
        "'; DROP TABLE x;--",
        "line\ninjection field=evil",  # newline reaches us only via a raw environ
        "x" * 200,  # oversized: rejected without reaching the parser
    ],
)
def test_resolve_request_id_rejects_and_warns_on_malformed_header(
    resolver_app: Flask,
    bad_value: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Inject via the WSGI environ rather than the test client's header dict: the
    # client validates headers and would reject a newline before our code runs,
    # but a value that somehow reaches request.headers must still be handled.
    with (
        resolver_app.test_request_context(environ_overrides={"HTTP_X_REQUEST_ID": bad_value}),
        caplog.at_level(logging.WARNING, logger=request_logging.logger.name),
    ):
        assert request.headers.get("X-Request-ID") == bad_value
        resolved = request_logging._resolve_request_id()

    uuid.UUID(resolved)  # falls back to a fresh, well-formed UUID
    assert any(r.levelno == logging.WARNING for r in caplog.records)
    # The value is logged only through repr(), which escapes control characters:
    # a newline in the header must not survive as a literal newline that could
    # forge a second log line (log injection). It appears escaped as "\n" instead.
    warning = next(r for r in caplog.records if r.levelno == logging.WARNING)
    rendered = warning.getMessage()
    assert "\n" not in rendered
    # And the rendered value is length-bounded regardless of how large the header is.
    assert len(rendered) < 200


@pytest.fixture(scope="module")
def request_context_app() -> Flask:
    """Shared Flask app for request-context-only tests."""
    flask_app = Flask(__name__)

    @flask_app.get("/items/<token>")
    def item_by_token(token: str) -> str:
        return token

    return flask_app


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
        path="/items/private-token-value",
        method="GET",
        request_id="req-123",
        status_code=204,
    ) as response:
        request_logging.log_request(response, duration_seconds=0.5)

    extra = captured_log["extra"]
    assert captured_log["level"] == logging.INFO
    assert extra["request_id"] == "req-123"
    assert extra["method"] == "GET"
    assert extra["path"] == "/items/<token>"
    assert "private-token-value" not in captured_log["args"]
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
    assert extra["path"] == "<unmatched>"
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
