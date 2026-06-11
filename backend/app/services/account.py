from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain.errors import ManagementApiCallError, ManagementApiUnavailableError
from app.middleware.auth.auth0 import ManagementApiClient, ManagementApiError
from app.repositories import users_repo as ur
from app.schema.api.requests.me import (
    ChangeEmailRequest,
    ChangeUsernameRequest,
    UpdateProfileRequest,
)
from app.schema.orm.core.user import User

logger = logging.getLogger(__name__)


def _mgmt(mgmt: ManagementApiClient | None) -> ManagementApiClient:
    """Return the management client or raise if not configured."""
    if mgmt is None:
        logger.error(
            "Auth0 Management API client is not configured. "
            "Set FLOWFORM_AUTH0_MGMT_ID and FLOWFORM_AUTH0_MGMT_SECRET."
        )
        raise ManagementApiUnavailableError()
    return mgmt


def _call_mgmt[**P, R](fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    """Call a management API method and translate errors into domain errors."""
    try:
        return fn(*args, **kwargs)
    except ManagementApiError as exc:
        logger.error(
            "Auth0 Management API call failed (HTTP %s, provider_error=%s)",
            exc.status_code,
            exc.provider_error,
        )
        raise ManagementApiCallError() from exc


class UserAccountService:
    """Handles account-level operations that may touch both the local DB and Auth0."""

    def update_profile(
        self,
        db: Session,
        *,
        actor: User,
        data: UpdateProfileRequest,
        mgmt: ManagementApiClient | None,
    ) -> User:
        """Update name, nickname, and/or picture.

        These fields only exist in Auth0 — no local DB column. Auth0 is
        updated first; if it fails the DB is never touched.
        """
        has_changes = any(
            v is not None for v in (data.display_name, data.nickname, data.picture)
        )
        if not has_changes:
            return actor

        _call_mgmt(
            _mgmt(mgmt).update_user,
            actor.auth0_user_id,
            display_name=data.display_name,
            nickname=data.nickname,
            picture=data.picture,
        )

        # display_name is also mirrored in our DB.
        if data.display_name is not None:
            ur.update_user(actor, email=actor.email, display_name=data.display_name)
            commit_with_err_handle(db)

        return actor

    def change_email(
        self,
        db: Session,
        *,
        actor: User,
        data: ChangeEmailRequest,
        mgmt: ManagementApiClient | None,
    ) -> User:
        """Change the account email address.

        Auth0 is updated first (and resets email_verified to false
        automatically). The local DB is only updated if Auth0 succeeds.
        """
        _call_mgmt(
            _mgmt(mgmt).update_user,
            actor.auth0_user_id,
            email=data.email,
        )

        ur.update_user_email(actor, email=data.email)
        commit_with_err_handle(db, contexts=[actor])
        return actor

    def change_username(
        self,
        *,
        actor: User,
        data: ChangeUsernameRequest,
        mgmt: ManagementApiClient | None,
    ) -> None:
        """Change the Auth0 username (no local DB column)."""
        _call_mgmt(
            _mgmt(mgmt).update_user,
            actor.auth0_user_id,
            username=data.username,
        )

    def change_password(
        self,
        *,
        actor: User,
        mgmt: ManagementApiClient | None,
    ) -> str:
        """Create a hosted Auth0 password-change URL for the current user."""
        return _call_mgmt(_mgmt(mgmt).create_password_change_ticket, actor.auth0_user_id)

    def clear_mfa_devices(
        self,
        *,
        actor: User,
        mgmt: ManagementApiClient | None,
    ) -> None:
        """Remove all enrolled MFA authenticators for the current user."""
        _call_mgmt(_mgmt(mgmt).clear_mfa_devices, actor.auth0_user_id)

    def delete_account(
        self,
        db: Session,
        *,
        actor: User,
        mgmt: ManagementApiClient | None,
    ) -> None:
        """Delete the user's Auth0 identity then remove the local DB row.

        Auth0 is deleted first so that a failed DB commit leaves no orphaned
        Auth0 user. The FK cascade/SET NULL on related rows handles cleanup.
        """
        _call_mgmt(_mgmt(mgmt).delete_user, actor.auth0_user_id)

        ur.delete_user(db, actor)
        # No contexts: deleting a user row cannot violate any translatable
        # constraint — all FK references use ON DELETE CASCADE or SET NULL.
        commit_with_err_handle(db)

    def resend_verification_email(
        self,
        *,
        actor: User,
        mgmt: ManagementApiClient | None,
    ) -> None:
        """Trigger an email-verification job for the current user."""
        _call_mgmt(_mgmt(mgmt).send_verification_email, actor.auth0_user_id)


account_service = UserAccountService()
