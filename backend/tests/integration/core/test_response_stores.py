from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.project import Project
from app.models.core.response_store import ResponseStore
from app.models.core.user import User


def test_response_store_unique_name_within_project(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    store_a = ResponseStore()
    store_a.project_id = project.id
    store_a.name = "warehouse"
    store_a.store_type = "platform_postgres"
    store_a.connection_reference = {"dsn": "x"}
    store_a.created_by_user_id = user.id
    db_session.add(store_a)
    db_session.flush()

    store_b = ResponseStore()
    store_b.project_id = project.id
    store_b.name = "warehouse"
    store_b.store_type = "platform_postgres"
    store_b.connection_reference = {"dsn": "y"}
    store_b.created_by_user_id = user.id
    db_session.add(store_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_response_stores_project_id_name", (
        f"Expected constraint 'uq_response_stores_project_id_name', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()
