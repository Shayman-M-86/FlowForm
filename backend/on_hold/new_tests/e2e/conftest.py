"""E2E fixtures for HTTP-level new tests."""

from __future__ import annotations

from collections.abc import Callable
from http.cookies import SimpleCookie
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Return a Flask test client for the configured lightweight app."""
    return app.test_client()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return default authenticated-request headers for E2E tests."""
    return {"Authorization": "Bearer test-access-token"}


@pytest.fixture
def respondent_cookies() -> SimpleCookie:
    """Return an empty respondent cookie jar."""
    return SimpleCookie()


@pytest.fixture
def api_post(client: FlaskClient) -> Callable[[str, dict[str, Any] | None], Any]:
    """Return a small JSON POST helper."""

    def _post(path: str, payload: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        return client.post(path, json=payload or {}, **kwargs)

    return _post
