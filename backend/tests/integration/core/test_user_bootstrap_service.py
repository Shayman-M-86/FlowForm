from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, scoped_session

from app.domain.errors import UserBootstrapConflictError
from app.schema.orm.core.user import User
from app.services.users import UserService
from tests.integration.core.factories import make_user


def test_bootstrap_user_creates_user(db_session: scoped_session[Session]) -> None:
    """bootstrap_user creates a local user row for a new Auth0 subject."""
    service = UserService()

    user, created = service.bootstrap_user(
        db_session,
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
    db_session: scoped_session[Session],
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
        db_session,
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


def test_bootstrap_user_raises_conflict_for_duplicate_email(
    db_session: scoped_session[Session],
) -> None:
    """bootstrap_user returns a clean conflict error when email uniqueness is violated."""
    existing = make_user(
        auth0_user_id="auth0|bootstrap-email-existing",
        email="duplicate@example.com",
        display_name="Existing",
    )
    db_session.add(existing)
    db_session.commit()

    service = UserService()

    with pytest.raises(UserBootstrapConflictError):
        service.bootstrap_user(
            db_session,
            auth0_user_id="auth0|bootstrap-email-other",
            email="duplicate@example.com",
            display_name="Other",
        )
