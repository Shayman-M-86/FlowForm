from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, scoped_session

from app.repositories import users_repo
from app.repositories.users_repo import _MAX_PUBLIC_ID_RETRIES, _PUBLIC_ID_CONSTRAINT


def test_create_user_generates_public_id(db_session: scoped_session[Session]) -> None:
    """public_id is populated by Postgres after flush."""
    user = users_repo.create_user(
        db_session,  # type: ignore
        auth0_user_id="auth0|pubid-new",
        email="pubid-new@example.com",
        display_name=None,
    )

    assert user.public_id is not None
    assert len(user.public_id) == 8
    assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in user.public_id)


def test_create_user_public_ids_are_unique(db_session: scoped_session[Session]) -> None:
    """Two different users receive distinct public_ids."""
    user_a = users_repo.create_user(
        db_session,  # type: ignore
        auth0_user_id="auth0|pubid-a",
        email="pubid-a@example.com",
        display_name=None,
    )
    user_b = users_repo.create_user(
        db_session,  # type: ignore
        auth0_user_id="auth0|pubid-b",
        email="pubid-b@example.com",
        display_name=None,
    )

    assert user_a.public_id != user_b.public_id


def test_retry_constants_are_correct() -> None:
    """Retry limit and constraint name match the schema."""
    assert _MAX_PUBLIC_ID_RETRIES == 5
    assert _PUBLIC_ID_CONSTRAINT == "uq_users_public_id"


def test_create_user_non_public_id_integrity_error_propagates(
    db_session: scoped_session[Session],
) -> None:
    """A duplicate email raises IntegrityError, not a silent retry."""
    from sqlalchemy.exc import IntegrityError

    users_repo.create_user(
        db_session,  # type: ignore
        auth0_user_id="auth0|pubid-email-1",
        email="shared@example.com",
        display_name=None,
    )
    db_session.commit()  # type: ignore

    with pytest.raises(IntegrityError):
        users_repo.create_user(
            db_session,  # type: ignore
            auth0_user_id="auth0|pubid-email-2",
            email="shared@example.com",
            display_name=None,
        )
