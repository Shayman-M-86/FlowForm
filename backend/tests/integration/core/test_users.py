from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.user import User
from tests.integration.core.factories import make_user


def test_user_can_be_created(db_session: scoped_session[Session]) -> None:
    """All fields are persisted and the server default populates created_at."""
    user = make_user(auth0_user_id="auth0|u1", email="u1@example.com", display_name="Alice")
    db_session.add(user)
    db_session.flush()

    saved = db_session.get(User, user.id)
    assert saved is not None, "User was not persisted"
    assert saved.auth0_user_id == "auth0|u1", f"auth0_user_id={saved.auth0_user_id!r}, expected 'auth0|u1'"
    assert saved.email == "u1@example.com", f"email={saved.email!r}, expected 'u1@example.com'"
    assert saved.display_name == "Alice", f"display_name={saved.display_name!r}, expected 'Alice'"
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_user_display_name_is_optional(db_session: scoped_session[Session]) -> None:
    """display_name is nullable — a user can be created without one."""
    user = make_user(auth0_user_id="auth0|nodisplay", email="nodisplay@example.com", display_name=None)
    db_session.add(user)
    db_session.flush()

    saved = db_session.get(User, user.id)
    assert saved is not None, "User was not persisted"
    assert saved.display_name is None, f"display_name={saved.display_name!r}, expected None"


def test_user_requires_auth0_user_id(db_session: scoped_session[Session]) -> None:
    """auth0_user_id is NOT NULL — omitting it raises an IntegrityError."""
    user = make_user()
    user.auth0_user_id = None  # type: ignore[assignment]
    db_session.add(user)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "auth0_user_id", (
        f"Expected NOT NULL violation on 'auth0_user_id', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_user_requires_email(db_session: scoped_session[Session]) -> None:
    """email is NOT NULL — omitting it raises an IntegrityError."""
    user = make_user()
    user.email = None  # type: ignore[assignment]
    db_session.add(user)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "email", (
        f"Expected NOT NULL violation on 'email', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_user_unique_email(db_session: scoped_session[Session]) -> None:
    """Two users cannot share the same email address."""
    user_a = make_user(auth0_user_id="auth0|a", email="dup@example.com")
    db_session.add(user_a)
    db_session.flush()

    user_b = make_user(auth0_user_id="auth0|b", email="dup@example.com")
    db_session.add(user_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "users_email_key", (
        f"Expected constraint 'users_email_key', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_user_unique_auth0_user_id(db_session: scoped_session[Session]) -> None:
    """Two users cannot share the same auth0_user_id."""
    user_a = make_user(auth0_user_id="auth0|same", email="one@example.com")
    db_session.add(user_a)
    db_session.flush()

    user_b = make_user(auth0_user_id="auth0|same", email="two@example.com")
    db_session.add(user_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "users_auth0_user_id_key", (
        f"Expected constraint 'users_auth0_user_id_key', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()
