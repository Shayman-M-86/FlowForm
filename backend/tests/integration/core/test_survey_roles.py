from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.project import Project
from app.models.core.survey_access import SurveyRole
from app.models.core.user import User
from tests.integration.core.factories import make_project, make_survey_role


def test_survey_role_can_be_created(
    db_session: scoped_session[Session], project: Project
) -> None:
    """All fields are persisted and the server default populates created_at."""
    role = make_survey_role(project.id, name="reviewer")
    db_session.add(role)
    db_session.flush()

    saved = db_session.get(SurveyRole, role.id)
    assert saved is not None, "SurveyRole was not persisted"
    assert saved.project_id == project.id, f"project_id={saved.project_id!r}, expected {project.id!r}"
    assert saved.name == "reviewer", f"name={saved.name!r}, expected 'reviewer'"
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_survey_role_unique_name_within_project(
    db_session: scoped_session[Session], project: Project
) -> None:
    """Two survey roles in the same project cannot share a name."""
    role_a = make_survey_role(project.id, name="analyst")
    db_session.add(role_a)
    db_session.flush()

    role_b = make_survey_role(project.id, name="analyst")
    db_session.add(role_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_survey_roles_project_id_name", (
        f"Expected constraint 'uq_survey_roles_project_id_name', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_role_same_name_allowed_across_projects(
    db_session: scoped_session[Session], user: User
) -> None:
    """Role name uniqueness is scoped to a project — different projects may reuse names."""
    project_a = make_project(user.id, name="A", slug="sr-proj-a")
    project_b = make_project(user.id, name="B", slug="sr-proj-b")
    db_session.add_all([project_a, project_b])
    db_session.flush()

    role_a = make_survey_role(project_a.id, name="analyst")
    role_b = make_survey_role(project_b.id, name="analyst")
    db_session.add_all([role_a, role_b])
    db_session.flush()

    assert role_a.id != role_b.id, (
        f"Expected distinct role IDs across projects, got id={role_a.id!r} for both"
    )


def test_survey_role_requires_name(
    db_session: scoped_session[Session], project: Project
) -> None:
    """name is NOT NULL — omitting it raises an IntegrityError."""
    role = SurveyRole()
    role.project_id = project.id
    role.name = None  # type: ignore[assignment]
    db_session.add(role)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "name", (
        f"Expected NOT NULL violation on 'name', got '{column}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_role_cascades_on_project_delete(
    db_session: scoped_session[Session], user: User
) -> None:
    """Deleting the project removes all its survey roles."""
    project = make_project(user.id, slug="sr-cascade-proj")
    db_session.add(project)
    db_session.flush()

    role = make_survey_role(project.id, name="to-delete")
    db_session.add(role)
    db_session.flush()

    role_id = role.id
    db_session.delete(project)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(SurveyRole, role_id) is None, (
        "SurveyRole should have been deleted when its project was deleted"
    )
