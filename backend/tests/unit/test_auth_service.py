from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.core.errors import AuthError
from app.schema.api.requests.auth import BootstrapUserRequest
from app.schema.orm.core.user import User
from app.services.auth import AuthService


def test_bootstrap_current_user_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """bootstrap_current_user verifies claims and delegates user persistence."""
    created_user = User(
        auth0_user_id="auth0|service-created",
        email="created@example.com",
        display_name="Created User",
    )
    created_user.id = 7

    user_service = Mock()
    user_service.bootstrap_user.return_value = (created_user, True)
    service = AuthService(user_service=user_service)

    from app.services import auth as auth_service_module

    monkeypatch.setattr(
        auth_service_module.auth,
        "verify_id_token",
        lambda _id_token: {
            "sub": "auth0|service-created",
            "email": "created@example.com",
            "name": "Created User",
        },
    )

    db = object()
    result = service.bootstrap_current_user(
        db,
        access_token_sub="auth0|service-created",
        payload=BootstrapUserRequest(id_token="raw-id-token"),
    )

    assert result.created is True
    assert result.user is created_user
    user_service.bootstrap_user.assert_called_once_with(
        db,
        auth0_user_id="auth0|service-created",
        email="created@example.com",
        display_name="Created User",
    )


def test_bootstrap_current_user_rejects_subject_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bootstrap_current_user raises when the ID token subject does not match."""
    user_service = Mock()
    service = AuthService(user_service=user_service)

    from app.services import auth as auth_service_module

    monkeypatch.setattr(
        auth_service_module.auth,
        "verify_id_token",
        lambda _id_token: {
            "sub": "auth0|id-token",
            "email": "created@example.com",
            "name": "Created User",
        },
    )

    with pytest.raises(AuthError) as exc_info:
        service.bootstrap_current_user(
            object(),
            access_token_sub="auth0|access-token",
            payload=BootstrapUserRequest(id_token="raw-id-token"),
        )

    assert exc_info.value.code == "TOKEN_SUBJECT_MISMATCH"
    user_service.bootstrap_user.assert_not_called()
