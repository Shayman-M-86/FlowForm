from __future__ import annotations

import pytest
from flask import Flask

from app.api.utils.errors import register_error_handlers
from app.api.v1 import auth as auth_api
from app.core.errors import AuthError
from app.core.extensions import auth
from app.schema.orm.core.user import User
from app.services.results import BootstrapCurrentUserResult


@pytest.fixture
def app() -> Flask:
    """Fresh Flask app with the auth bootstrap route registered."""
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    register_error_handlers(flask_app)
    flask_app.register_blueprint(auth_api.auth_bp, url_prefix="/api/v1/auth")
    return flask_app


@pytest.fixture
def client(app: Flask):
    """Flask test client for auth bootstrap route tests."""
    return app.test_client()


def test_bootstrap_user_returns_created_response(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bootstrap-user returns 201 and the normalized user payload on first create."""
    created_user = User(
        auth0_user_id="auth0|route-created",
        email="created@example.com",
        display_name="Created User",
    )
    created_user.id = 42

    monkeypatch.setattr(auth, "_extract_bearer_token", lambda: "token")
    monkeypatch.setattr(auth, "_verify_access_token", lambda _token: {"sub": "auth0|route-created"})
    monkeypatch.setattr(auth_api, "get_core_db", lambda: object())
    monkeypatch.setattr(
        auth_api.auth_service,
        "bootstrap_current_user",
        lambda _db, access_token_sub, payload: BootstrapCurrentUserResult(
            user=created_user,
            created=True,
        ),
    )

    response = client.post(
        "/api/v1/auth/bootstrap-user",
        json={"id_token": "raw-id-token"},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "created": True,
        "user": {
            "id": 42,
            "auth0_user_id": "auth0|route-created",
            "email": "created@example.com",
            "display_name": "Created User",
        },
    }


def test_bootstrap_user_rejects_subject_mismatch(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bootstrap-user rejects mismatched access-token and ID-token subjects."""
    monkeypatch.setattr(auth, "_extract_bearer_token", lambda: "token")
    monkeypatch.setattr(auth, "_verify_access_token", lambda _token: {"sub": "auth0|access"})
    monkeypatch.setattr(auth_api, "get_core_db", lambda: object())
    monkeypatch.setattr(
        auth_api.auth_service,
        "bootstrap_current_user",
        lambda _db, access_token_sub, payload: (_ for _ in ()).throw(
            AuthError(
                message="ID token subject did not match the access token subject.",
                code="TOKEN_SUBJECT_MISMATCH",
                status_code=401,
            )
        ),
    )

    response = client.post(
        "/api/v1/auth/bootstrap-user",
        json={"id_token": "raw-id-token"},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 401
    assert response.get_json()["code"] == "TOKEN_SUBJECT_MISMATCH"
