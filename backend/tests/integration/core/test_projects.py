from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.project import Project, ProjectMembership
from app.models.core.user import User
from tests.integration.core.factories import make_project, make_project_role


def test_project_unique_slug(db_session: scoped_session[Session], user: User) -> None:
    project_a = make_project(user.id, name="One", slug="same")
    db_session.add(project_a)
    db_session.flush()

    project_b = make_project(user.id, name="Two", slug="same")
    db_session.add(project_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_project_role_unique_name_within_project(db_session: scoped_session[Session], project: Project) -> None:
    role_a = make_project_role(project.id, name="editor")
    db_session.add(role_a)
    db_session.flush()

    role_b = make_project_role(project.id, name="editor")
    db_session.add(role_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_project_membership_unique_user_project(
    db_session: scoped_session[Session], user: User, project: Project
) -> None:
    membership_a = ProjectMembership()
    membership_a.user_id = user.id
    membership_a.project_id = project.id
    db_session.add(membership_a)
    db_session.flush()

    membership_b = ProjectMembership()
    membership_b.user_id = user.id
    membership_b.project_id = project.id
    db_session.add(membership_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name

    assert constraint == "uq_project_memberships_user_project", (
        f"Wrong constraint triggered.\n"
        f"Expected: uq_project_memberships_user_project\n"
        f"Actual:   {constraint}\n\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()
