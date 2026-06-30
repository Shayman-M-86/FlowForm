from __future__ import annotations

from sqlalchemy.orm import Session

from app.schema.orm.core.user import User
from app.services.users import UserService
from tests.integration.core.factories import make_user


def test_bootstrap_user_creates_user(db_session: Session) -> None:
    """bootstrap_user creates a local user row for a new Auth0 subject."""
    service = UserService()

    user, created = service.bootstrap_user(
        db_session, # type: ignore
        auth0_user_id="auth0|bootstrap-new",
        email="bootstrap-new@example.com",
        display_name="Bootstrap New",
    )

    assert created is True
    assert user.id is not None
    assert user.auth0_user_id == "auth0|bootstrap-new"
    assert user.email == "bootstrap-new@example.com"
    assert user.display_name == "Bootstrap New"


def test_bootstrap_user_updates_existing_user(
    db_session: Session,
) -> None:
    """bootstrap_user syncs email and display name for an existing Auth0 subject."""
    existing = make_user(
        auth0_user_id="auth0|bootstrap-existing",
        email="old@example.com",
        display_name="Old Name",
    )
    db_session.add(existing)
    db_session.commit()

    service = UserService()
    user, created = service.bootstrap_user(
        db_session, # type: ignore
        auth0_user_id="auth0|bootstrap-existing",
        email="new@example.com",
        display_name="New Name",
    )

    refreshed = db_session.get(User, existing.id)
    assert created is False
    assert user.id == existing.id
    assert refreshed is not None
    assert refreshed.email == "new@example.com"
    assert refreshed.display_name == "New Name"


def test_bootstrap_user_allows_duplicate_email_for_new_identity(
    db_session: Session,
) -> None:
    """A second Auth0 identity sharing an email bootstraps into its own user row."""
    existing = make_user(
        auth0_user_id="auth0|bootstrap-email-existing",
        email="duplicate@example.com",
        display_name="Existing",
    )
    db_session.add(existing)
    db_session.commit()

    service = UserService()

    user, created = service.bootstrap_user(
        db_session,  # type: ignore
        auth0_user_id="auth0|bootstrap-email-other",
        email="duplicate@example.com",
        display_name="Other",
    )

    assert created is True
    assert user.id != existing.id
    assert user.email == existing.email
