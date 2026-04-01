from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from tests.integration.core.factories import make_user


def test_user_unique_email(db_session: scoped_session[Session]) -> None:
    user_a = make_user(auth0_user_id="auth0|a", email="dup@example.com")
    db_session.add(user_a)
    db_session.flush()

    user_b = make_user(auth0_user_id="auth0|b", email="dup@example.com")
    db_session.add(user_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_user_unique_auth0_user_id(db_session: scoped_session[Session]) -> None:
    user_a = make_user(auth0_user_id="auth0|same", email="one@example.com")
    db_session.add(user_a)
    db_session.flush()

    user_b = make_user(auth0_user_id="auth0|same", email="two@example.com")
    db_session.add(user_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()
