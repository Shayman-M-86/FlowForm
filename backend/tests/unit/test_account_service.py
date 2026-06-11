from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.domain.errors import ManagementApiCallError
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


def test_account_management_errors_return_generic_message(monkeypatch: pytest.MonkeyPatch) -> None:
    user = User()
    user.id = 1
    user.auth0_user_id = "auth0|user-123"
    user.email = "user@example.com"
    user.display_name = "Old Name"
    update_user = Mock()
    monkeypatch.setattr(account_module.ur, "update_user", update_user)

    with pytest.raises(ManagementApiCallError) as exc_info:
        UserAccountService().update_profile(
            Mock(),
            actor=user,
            data=UpdateProfileRequest(display_name="New Name"),
            mgmt=FailingManagementApiClient(),  # type: ignore[arg-type]
        )

    assert exc_info.value.message == "Account management could not be completed at this time."
    assert "auth0|user-123" not in exc_info.value.message
    update_user.assert_not_called()


def test_change_password_returns_hosted_ticket_url() -> None:
    user = User()
    user.id = 1
    user.auth0_user_id = "auth0|user-123"
    mgmt = PasswordTicketManagementApiClient()

    ticket_url = UserAccountService().change_password(
        actor=user,
        mgmt=mgmt,  # type: ignore[arg-type]
    )

    assert ticket_url == "https://example.auth0.com/password-change-ticket"
    assert mgmt.auth0_user_id == "auth0|user-123"
