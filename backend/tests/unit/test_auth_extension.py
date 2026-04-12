from __future__ import annotations

import pytest
from flask import Flask, jsonify

from app.api.utils.errors import register_error_handlers
from app.middleware.auth import auth_errors
from app.middleware.auth.auth0 import AuthExtension


@pytest.fixture
def auth_extension() -> AuthExtension:
    return AuthExtension()


@pytest.fixture
def app(auth_extension: AuthExtension) -> Flask:
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    register_error_handlers(flask_app)

    @flask_app.get("/optional-auth")
    @auth_extension.optional_auth()
    def optional_auth_route():
        return jsonify(
            {
                "claims": auth_extension.get_optional_current_claims(),
                "sub": auth_extension.get_optional_current_user_sub(),
            }
        )

    @flask_app.get("/require-auth")
    @auth_extension.require_auth()
    def require_auth_route():
        return jsonify(
            {
                "claims": auth_extension.get_current_claims(),
                "sub": auth_extension.get_current_user_sub(),
            }
        )

    return flask_app


@pytest.fixture
def client(app: Flask):
    return app.test_client()


def test_optional_auth_allows_anonymous_request(
    client,
    auth_extension: AuthExtension,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_extension, "_verify_access_token", lambda _token: pytest.fail("unexpected"))

    response = client.get("/optional-auth")

    assert response.status_code == 200
    assert response.get_json() == {"claims": None, "sub": None}


def test_optional_auth_allows_blank_authorization_header(
    client,
    auth_extension: AuthExtension,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_extension, "_verify_access_token", lambda _token: pytest.fail("unexpected"))

    response = client.get("/optional-auth", headers={"Authorization": "   "})

    assert response.status_code == 200
    assert response.get_json() == {"claims": None, "sub": None}


def test_optional_auth_populates_context_for_valid_token(
    client,
    auth_extension: AuthExtension,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claims = {"sub": "auth0|optional-user", "scope": "read:projects"}
    monkeypatch.setattr(auth_extension, "_verify_access_token", lambda _token: claims)

    response = client.get("/optional-auth", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    assert response.get_json() == {"claims": claims, "sub": "auth0|optional-user"}


def test_optional_auth_rejects_invalid_header_shape(client) -> None:
    response = client.get("/optional-auth", headers={"Authorization": "Basic abc123"})

    assert response.status_code == 401
    assert response.get_json()["code"] == "INVALID_AUTHORIZATION_HEADER"


def test_optional_auth_rejects_invalid_token(
    client,
    auth_extension: AuthExtension,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_extension,
        "_verify_access_token",
        lambda _token: (_ for _ in ()).throw(
            auth_errors.invalid_access_token("bad token", status_code=401)
        ),
    )

    response = client.get("/optional-auth", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
    assert response.get_json()["code"] == "INVALID_ACCESS_TOKEN"


def test_require_auth_still_rejects_missing_header(client) -> None:
    response = client.get("/require-auth")

    assert response.status_code == 401
    assert response.get_json()["code"] == "MISSING_AUTHORIZATION_HEADER"


def test_require_auth_still_populates_context_for_valid_token(
    client,
    auth_extension: AuthExtension,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claims = {"sub": "auth0|required-user", "scope": "read:projects"}
    monkeypatch.setattr(auth_extension, "_verify_access_token", lambda _token: claims)

    response = client.get("/require-auth", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    assert response.get_json() == {"claims": claims, "sub": "auth0|required-user"}
