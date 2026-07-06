from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.cache import get_app_cache
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


def _mgmt() -> ManagementApiClient:
    """Return the app's Auth0 Management API client or raise if not configured.

    Read lazily from app.core.extensions.auth on every call, not cached on
    the service: account_service is constructed when its owning blueprint
    module is first imported, which happens before AuthExtension.init_app()
    has run (see app/api/v1/account/__init__.py, imported transitively by
    app/core/factory.py at module load time). By the time a request is
    actually handled, init_app() has long since completed and auth.mgmt
    reflects the real configured client.
    """
    from app.core.extensions import auth

    if auth.mgmt is None:
        logger.error(
            "Auth0 Management API client is not configured. "
            "Set FLOWFORM_AUTH0_MGMT_ID and FLOWFORM_AUTH0_MGMT_SECRET_FILE."
        )
        raise ManagementApiUnavailableError()
    return auth.mgmt


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
            _mgmt().update_user,
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
    ) -> User:
        """Change the account email address.

        Auth0 is updated first (and resets email_verified to false
        automatically). The local DB is only updated if Auth0 succeeds.
        """
        _call_mgmt(
            _mgmt().update_user,
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
    ) -> None:
        """Change the Auth0 username (no local DB column)."""
        _call_mgmt(
            _mgmt().update_user,
            actor.auth0_user_id,
            username=data.username,
        )

    def change_password(
        self,
        *,
        actor: User,
    ) -> str:
        """Create a hosted Auth0 password-change URL for the current user."""
        return _call_mgmt(_mgmt().create_password_change_ticket, actor.auth0_user_id)

    def clear_mfa_devices(
        self,
        *,
        actor: User,
    ) -> None:
        """Remove all enrolled MFA authenticators for the current user."""
        _call_mgmt(_mgmt().clear_mfa_devices, actor.auth0_user_id)

    def delete_account(
        self,
        db: Session,
        *,
        actor: User,
    ) -> None:
        """Delete the user's Auth0 identity then remove the local DB row.

        Auth0 is deleted first so that a failed DB commit leaves no orphaned
        Auth0 user. The FK cascade/SET NULL on related rows handles cleanup.
        """
        _call_mgmt(_mgmt().delete_user, actor.auth0_user_id)

        ur.delete_user(db, actor)
        # No contexts: deleting a user row cannot violate any translatable
        # constraint — all FK references use ON DELETE CASCADE or SET NULL.
        commit_with_err_handle(db)

    def resend_verification_email(
        self,
        *,
        actor: User,
    ) -> None:
        """Trigger an email-verification job for the current user."""
        _call_mgmt(_mgmt().send_verification_email, actor.auth0_user_id)

    def check_email_verified(
        self,
        db: Session,
        *,
        actor: User,
    ) -> bool:
        """Re-check email verification status live against Auth0.

        The cached ID-token claim only updates on token refresh/re-login, so
        a user who verifies in another tab won't see it reflected until
        then. This forces a live lookup and persists the result locally so
        it also unblocks the invitation-accept gate immediately.

        The Auth0 lookup itself goes through a short-lived in-process cache
        (app/cache/account.py): repeated checks for the same user within
        the TTL -- refresh spam, multiple tabs, a user re-clicking, the
        frontend's own poll -- are answered from memory instead of each
        making a fresh Management API call. Both live verified and live
        unverified results are cached briefly, so a user who verifies in
        another tab may wait out this small TTL before the next live Auth0
        check. users.email_verified in the database remains the durable
        source of truth that every other request actually trusts.
        """
        if actor.email_verified:
            return True

        live_verified = get_app_cache().account.email_verified.get_or_load(
            actor.auth0_user_id,
            lambda: _call_mgmt(_mgmt().get_user_email_verified, actor.auth0_user_id),
        )

        if live_verified:
            ur.set_email_verified(actor, email_verified=True)
            commit_with_err_handle(db)
        return live_verified
