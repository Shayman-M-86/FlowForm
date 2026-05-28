from __future__ import annotations

from types import SimpleNamespace

import pytest  # type: ignore[import]
from flask import Flask, jsonify
from pydantic import SecretStr

from app.api.utils.errors import register_error_handlers
from app.core.errors import ConfigError
from app.middleware.auth import auth0 as auth0_module
from app.middleware.auth import auth_errors
from app.middleware.auth.auth0 import AuthExtension, ManagementApiClient, ManagementApiError


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
        lambda _token: (_ for _ in ()).throw(auth_errors.invalid_access_token("bad token", status_code=401)),
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


def test_init_app_leaves_mgmt_none_when_not_configured(
    auth_extension: AuthExtension,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flask_app = Flask(__name__)
    flask_app.extensions["settings"] = SimpleNamespace(
        flowform=SimpleNamespace(
            auth0=SimpleNamespace(
                audience="https://api.example.test",
                domain="example.auth0.com",
                mgmt=None,
            )
        )
    )
    monkeypatch.setattr(auth0_module, "ApiClient", lambda _options: object())

    auth_extension.init_app(flask_app)

    assert auth_extension.mgmt is None


def test_init_app_validates_management_client(
    auth_extension: AuthExtension,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeManagementApiClient:
        validated = False

        def __init__(self, *, domain: str, client_id: str, client_secret: str) -> None:
            self.domain = domain
            self.client_id = client_id
            self.client_secret = client_secret

        def validate_connection(self) -> None:
            self.validated = True

    flask_app = Flask(__name__)
    flask_app.extensions["settings"] = SimpleNamespace(
        flowform=SimpleNamespace(
            auth0=SimpleNamespace(
                audience="https://api.example.test",
                domain="example.auth0.com",
                mgmt=SimpleNamespace(
                    id="client-id",
                    secret=SecretStr("client-secret"),
                ),
            )
        )
    )
    monkeypatch.setattr(auth0_module, "ApiClient", lambda _options: object())
    monkeypatch.setattr(auth0_module, "ManagementApiClient", FakeManagementApiClient)

    auth_extension.init_app(flask_app)

    assert isinstance(auth_extension.mgmt, FakeManagementApiClient)
    assert auth_extension.mgmt.domain == "example.auth0.com"
    assert auth_extension.mgmt.client_id == "client-id"
    assert auth_extension.mgmt.client_secret == "client-secret"
    assert auth_extension.mgmt.validated is True


def test_init_app_rejects_failed_management_validation(
    auth_extension: AuthExtension,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeManagementApiClient:
        def __init__(self, *, domain: str, client_id: str, client_secret: str) -> None:
            pass

        def validate_connection(self) -> None:
            raise ManagementApiError(
                status_code=403,
                provider_error="access_denied",
                provider_message="Client grant is missing.",
            )

    flask_app = Flask(__name__)
    flask_app.extensions["settings"] = SimpleNamespace(
        flowform=SimpleNamespace(
            auth0=SimpleNamespace(
                audience="https://api.example.test",
                domain="example.auth0.com",
                mgmt=SimpleNamespace(
                    id="client-id",
                    secret=SecretStr("client-secret"),
                ),
            )
        )
    )
    monkeypatch.setattr(auth0_module, "ApiClient", lambda _options: object())
    monkeypatch.setattr(auth0_module, "ManagementApiClient", FakeManagementApiClient)

    with pytest.raises(ConfigError, match="client grant and scopes"):
        auth_extension.init_app(flask_app)

    assert auth_extension.mgmt is None


def test_management_token_error_is_translated(monkeypatch: pytest.MonkeyPatch) -> None:
    class TokenResponse:
        ok = False
        status_code = 403
        text = "forbidden"

        def json(self) -> dict[str, str]:
            return {
                "error": "access_denied",
                "error_description": "Client is not authorized to access the Management API.",
            }

    monkeypatch.setattr(auth0_module.requests, "post", lambda *_args, **_kwargs: TokenResponse())

    client = ManagementApiClient(
        domain="example.auth0.com",
        client_id="client-id",
        client_secret="client-secret",
    )

    with pytest.raises(ManagementApiError) as exc_info:
        client._fetch_token()

    assert exc_info.value.status_code == 403
    assert exc_info.value.provider_error == "access_denied"
    assert exc_info.value.provider_message == "Client is not authorized to access the Management API."
    assert str(exc_info.value) == "Auth0 Management API request failed."


def test_management_token_response_requires_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    class TokenResponse:
        ok = True
        status_code = 200
        text = "{}"

        def json(self) -> dict[str, str]:
            return {}

    monkeypatch.setattr(auth0_module.requests, "post", lambda *_args, **_kwargs: TokenResponse())

    client = ManagementApiClient(
        domain="example.auth0.com",
        client_id="client-id",
        client_secret="client-secret",
    )

    with pytest.raises(ManagementApiError) as exc_info:
        client._fetch_token()

    assert exc_info.value.status_code == 200
    assert exc_info.value.provider_error == "invalid_token_response"
    assert str(exc_info.value) == "Auth0 Management API request failed."


def test_management_token_request_includes_required_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    class TokenResponse:
        ok = True
        status_code = 200
        text = "{}"

        def json(self) -> dict[str, str | int]:
            return {
                "access_token": "access-token",
                "expires_in": 3600,
                "scope": "create:user_tickets create:users delete:guardian_enrollments delete:users update:users",
            }

    captured: dict[str, object] = {}

    def fake_post(*_args: object, **kwargs: object) -> TokenResponse:
        captured["json"] = kwargs.get("json")
        return TokenResponse()

    monkeypatch.setattr(auth0_module.requests, "post", fake_post)

    client = ManagementApiClient(
        domain="example.auth0.com",
        client_id="client-id",
        client_secret="client-secret",
    )

    client.validate_connection()

    assert captured["json"] == {
        "grant_type": "client_credentials",
        "client_id": "client-id",
        "client_secret": "client-secret",
        "audience": "https://example.auth0.com/api/v2/",
        "scope": "create:user_tickets create:users delete:guardian_enrollments delete:users update:users",
    }


def test_management_token_response_requires_granted_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    class TokenResponse:
        ok = True
        status_code = 200
        text = "{}"

        def json(self) -> dict[str, str | int]:
            return {
                "access_token": "access-token",
                "expires_in": 3600,
                "scope": "create:users delete:guardian_enrollments delete:users update:users",
            }

    monkeypatch.setattr(auth0_module.requests, "post", lambda *_args, **_kwargs: TokenResponse())

    client = ManagementApiClient(
        domain="example.auth0.com",
        client_id="client-id",
        client_secret="client-secret",
    )

    with pytest.raises(ManagementApiError) as exc_info:
        client.validate_connection()

    assert exc_info.value.status_code == 200
    assert exc_info.value.provider_error == "missing_management_api_scope"
    assert exc_info.value.provider_message == (
        "Management API token is missing required scope(s): create:user_tickets."
    )


def test_management_user_operation_error_does_not_expose_user_identifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UserResponse:
        ok = False
        status_code = 403
        text = "auth0|user-123 is forbidden"

        def json(self) -> dict[str, str]:
            return {
                "error": "forbidden",
                "message": "auth0|user-123 is forbidden",
            }

    monkeypatch.setattr(auth0_module.requests, "request", lambda *_args, **_kwargs: UserResponse())

    client = ManagementApiClient(
        domain="example.auth0.com",
        client_id="client-id",
        client_secret="client-secret",
    )
    client._access_token = "cached-token"
    client._token_expires_at = 10**12
    client._token_scopes = {"update:users"}

    with pytest.raises(ManagementApiError) as exc_info:
        client.update_user("auth0|user-123", display_name="New Name")

    assert exc_info.value.status_code == 403
    assert exc_info.value.provider_error == "forbidden"
    assert exc_info.value.provider_message == "auth0|user-123 is forbidden"
    assert "auth0|user-123" not in str(exc_info.value)


def test_management_creates_password_change_ticket(monkeypatch: pytest.MonkeyPatch) -> None:
    class TicketResponse:
        ok = True
        status_code = 201
        text = '{"ticket":"https://example.auth0.com/password-change-ticket"}'

        def json(self) -> dict[str, str]:
            return {"ticket": "https://example.auth0.com/password-change-ticket"}

    captured: dict[str, object] = {}

    def fake_request(method: str, url: str, **kwargs: object) -> TicketResponse:
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return TicketResponse()

    monkeypatch.setattr(auth0_module.requests, "request", fake_request)

    client = ManagementApiClient(
        domain="example.auth0.com",
        client_id="client-id",
        client_secret="client-secret",
    )
    client._access_token = "cached-token"
    client._token_expires_at = 10**12
    client._token_scopes = {"create:user_tickets"}

    ticket_url = client.create_password_change_ticket("auth0|user-123")

    assert ticket_url == "https://example.auth0.com/password-change-ticket"
    assert captured == {
        "method": "POST",
        "url": "https://example.auth0.com/api/v2/tickets/password-change",
        "json": {"user_id": "auth0|user-123"},
    }


def test_management_password_change_ticket_response_requires_ticket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TicketResponse:
        ok = True
        status_code = 201
        text = "{}"

        def json(self) -> dict[str, str]:
            return {}

    monkeypatch.setattr(auth0_module.requests, "request", lambda *_args, **_kwargs: TicketResponse())

    client = ManagementApiClient(
        domain="example.auth0.com",
        client_id="client-id",
        client_secret="client-secret",
    )
    client._access_token = "cached-token"
    client._token_expires_at = 10**12
    client._token_scopes = {"create:user_tickets"}

    with pytest.raises(ManagementApiError) as exc_info:
        client.create_password_change_ticket("auth0|user-123")

    assert exc_info.value.status_code == 201
    assert exc_info.value.provider_error == "invalid_ticket_response"
