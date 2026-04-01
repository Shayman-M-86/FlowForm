from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from tests.integration.core.factories import make_user


def test_user_unique_email(db_session: scoped_session[Session]) -> None:
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
        f"Expected constraint 'users_email_key', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_user_unique_auth0_user_id(db_session: scoped_session[Session]) -> None:
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
        f"Expected constraint 'users_auth0_user_id_key', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()
