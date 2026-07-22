from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domain.errors import ManagementApiCallError, PasswordChangeUnsupportedError
from app.middleware.auth.auth0 import ManagementApiError
from app.schema.api.requests.me import UpdateProfileRequest
from app.schema.orm.core.user import User
from app.services import account as account_module
from app.services.account import UserAccountService


class FailingManagementApiClient:
    def update_user(self, *_args: object, **_kwargs: object) -> None:
        raise ManagementApiError(
            status_code=403,
            provider_error="forbidden",
            provider_message="auth0|user-123 is forbidden",
        )


class PasswordTicketManagementApiClient:
    def __init__(self) -> None:
        self.auth0_user_id: str | None = None

    def create_password_change_ticket(self, auth0_user_id: str) -> str:
        self.auth0_user_id = auth0_user_id
        return "https://example.auth0.com/password-change-ticket"


class UnsupportedPasswordTicketManagementApiClient:
    def create_password_change_ticket(self, _auth0_user_id: str) -> str:
        raise ManagementApiError(
            status_code=400,
            provider_error="operation_not_supported",
            provider_message="The user's main connection does not support this operation",
        )


class CachedEmailVerified:
    def __init__(self) -> None:
        self.values: dict[str, bool] = {}

    def get_or_load(self, key: str, loader: Callable[[], bool]) -> bool:
        if key not in self.values:
            self.values[key] = loader()
        return self.values[key]


def test_account_management_errors_return_generic_message(monkeypatch: pytest.MonkeyPatch) -> None:
    user = User()
    user.id = 1
    user.auth0_user_id = "auth0|user-123"
    user.email = "user@example.com"
    user.display_name = "Old Name"
    update_user = Mock()
    monkeypatch.setattr(account_module.ur, "update_user", update_user)
    monkeypatch.setattr(account_module, "_mgmt", lambda: FailingManagementApiClient())

    with pytest.raises(ManagementApiCallError) as exc_info:
        UserAccountService().update_profile(
            Mock(),
            actor=user,
            data=UpdateProfileRequest(display_name="New Name"),
        )

    assert exc_info.value.message == "Account management could not be completed at this time."
    assert "auth0|user-123" not in exc_info.value.message
    update_user.assert_not_called()


def test_change_password_returns_hosted_ticket_url(monkeypatch: pytest.MonkeyPatch) -> None:
    user = User()
    user.id = 1
    user.auth0_user_id = "auth0|user-123"
    mgmt = PasswordTicketManagementApiClient()
    monkeypatch.setattr(account_module, "_mgmt", lambda: mgmt)

    ticket_url = UserAccountService().change_password(
        actor=user,
    )

    assert ticket_url == "https://example.auth0.com/password-change-ticket"
    assert mgmt.auth0_user_id == "auth0|user-123"


def test_change_password_reports_unsupported_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    user = User()
    user.id = 1
    user.auth0_user_id = "google-oauth2|user-123"
    monkeypatch.setattr(account_module, "_mgmt", lambda: UnsupportedPasswordTicketManagementApiClient())

    with pytest.raises(PasswordChangeUnsupportedError) as exc_info:
        UserAccountService().change_password(actor=user)

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "PASSWORD_CHANGE_UNSUPPORTED"
    assert "google-oauth2|user-123" not in exc_info.value.message


def test_check_email_verified_caches_unverified_result(monkeypatch: pytest.MonkeyPatch) -> None:
    user = User()
    user.id = 1
    user.auth0_user_id = "auth0|user-123"
    user.email_verified = False
    mgmt = Mock()
    mgmt.get_user_email_verified = Mock(return_value=False)
    cache = CachedEmailVerified()

    monkeypatch.setattr(account_module, "_mgmt", lambda: mgmt)
    monkeypatch.setattr(
        account_module,
        "get_app_cache",
        lambda: SimpleNamespace(account=SimpleNamespace(email_verified=cache)),
    )
    set_email_verified = Mock(
        side_effect=lambda actor, *, email_verified: setattr(actor, "email_verified", email_verified)
    )
    commit = Mock()
    monkeypatch.setattr(account_module.ur, "set_email_verified", set_email_verified)
    monkeypatch.setattr(account_module, "commit_with_err_handle", commit)

    service = UserAccountService()

    assert service.check_email_verified(Mock(), actor=user) is False
    assert service.check_email_verified(Mock(), actor=user) is False
    mgmt.get_user_email_verified.assert_called_once_with(user.auth0_user_id)
    set_email_verified.assert_not_called()
    commit.assert_not_called()


def test_check_email_verified_persists_cached_verified_result(monkeypatch: pytest.MonkeyPatch) -> None:
    user = User()
    user.id = 1
    user.auth0_user_id = "auth0|user-123"
    user.email_verified = False
    mgmt = Mock()
    mgmt.get_user_email_verified = Mock(return_value=True)
    cache = CachedEmailVerified()
    db = Mock()

    monkeypatch.setattr(account_module, "_mgmt", lambda: mgmt)
    monkeypatch.setattr(
        account_module,
        "get_app_cache",
        lambda: SimpleNamespace(account=SimpleNamespace(email_verified=cache)),
    )
    set_email_verified = Mock()
    commit = Mock()
    monkeypatch.setattr(account_module.ur, "set_email_verified", set_email_verified)
    monkeypatch.setattr(account_module, "commit_with_err_handle", commit)

    service = UserAccountService()

    assert service.check_email_verified(db, actor=user) is True
    assert service.check_email_verified(db, actor=user) is True
    mgmt.get_user_email_verified.assert_called_once_with(user.auth0_user_id)
    assert set_email_verified.call_count == 2
    assert commit.call_count == 2
