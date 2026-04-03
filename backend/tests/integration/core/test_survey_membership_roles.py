from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import ForeignKeyViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.schema.orm.core.project import Project, ProjectMembership
from app.schema.orm.core.survey import Survey
from app.schema.orm.core.survey_access import SurveyMembershipRole
from app.schema.orm.core.user import User
from tests.integration.core.factories import make_project, make_survey, make_survey_role, make_user


def _make_membership(
    db_session: scoped_session[Session], user: User, project: Project
) -> ProjectMembership:
    """Helper: create and flush a ProjectMembership for the given user and project."""
    membership = ProjectMembership()
    membership.user_id = user.id
    membership.project_id = project.id
    db_session.add(membership)
    db_session.flush()
    return membership


def test_survey_membership_role_can_be_created(
    db_session: scoped_session[Session],
    user: User,
    project: Project,
    survey: Survey,
) -> None:
    """All three composite FKs resolve to the same project — record is persisted."""
    membership = _make_membership(db_session, user, project)
    role = make_survey_role(project.id, name="reviewer")
    db_session.add(role)
    db_session.flush()

    smr = SurveyMembershipRole()
    smr.project_id = project.id
    smr.survey_id = survey.id
    smr.membership_id = membership.id
    smr.role_id = role.id
    db_session.add(smr)
    db_session.flush()

    saved = db_session.get(SurveyMembershipRole, (survey.id, membership.id))
    assert saved is not None, "SurveyMembershipRole was not persisted"
    assert saved.project_id == project.id, f"project_id={saved.project_id!r}, expected {project.id!r}"
    assert saved.role_id == role.id, f"role_id={saved.role_id!r}, expected {role.id!r}"
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_survey_membership_role_rejects_survey_from_different_project(
    db_session: scoped_session[Session],
    user: User,
    project: Project,
) -> None:
    """survey_id must belong to the same project as project_id."""
    other_project = make_project(user.id, name="Other", slug="smr-other-proj-s")
    db_session.add(other_project)
    db_session.flush()

    # response_store needed for survey — borrow the project's store indirectly via make_survey
    other_user = make_user(auth0_user_id="auth0|smr-s", email="smr-s@example.com")
    db_session.add(other_user)
    db_session.flush()

    from tests.integration.core.factories import make_response_store
    other_store = make_response_store(other_project.id, other_user.id, name="smr-store-s")
    db_session.add(other_store)
    db_session.flush()

    survey_in_other = make_survey(other_project.id, other_store.id, other_user.id, title="Other Survey")
    db_session.add(survey_in_other)
    db_session.flush()

    membership = _make_membership(db_session, user, project)
    role = make_survey_role(project.id, name="reviewer")
    db_session.add(role)
    db_session.flush()

    smr = SurveyMembershipRole()
    smr.project_id = project.id          # project A
    smr.survey_id = survey_in_other.id   # survey belongs to other_project — mismatch
    smr.membership_id = membership.id
    smr.role_id = role.id
    db_session.add(smr)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(ForeignKeyViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "fk_survey_membership_roles_survey_same_project", (
        f"Expected constraint 'fk_survey_membership_roles_survey_same_project', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_membership_role_rejects_membership_from_different_project(
    db_session: scoped_session[Session],
    user: User,
    project: Project,
    survey: Survey,
) -> None:
    """membership_id must belong to the same project as project_id."""
    other_project = make_project(user.id, name="Other", slug="smr-other-proj-m")
    db_session.add(other_project)
    db_session.flush()

    membership_in_other = _make_membership(db_session, user, other_project)

    role = make_survey_role(project.id, name="reviewer")
    db_session.add(role)
    db_session.flush()

    smr = SurveyMembershipRole()
    smr.project_id = project.id
    smr.survey_id = survey.id
    smr.membership_id = membership_in_other.id  # membership belongs to other_project — mismatch
    smr.role_id = role.id
    db_session.add(smr)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(ForeignKeyViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "fk_survey_membership_roles_membership_same_project", (
        f"Expected constraint 'fk_survey_membership_roles_membership_same_project', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_membership_role_rejects_role_from_different_project(
    db_session: scoped_session[Session],
    user: User,
    project: Project,
    survey: Survey,
) -> None:
    """role_id must belong to the same project as project_id."""
    other_project = make_project(user.id, name="Other", slug="smr-other-proj-r")
    db_session.add(other_project)
    db_session.flush()

    role_in_other = make_survey_role(other_project.id, name="analyst")
    db_session.add(role_in_other)
    db_session.flush()

    membership = _make_membership(db_session, user, project)

    smr = SurveyMembershipRole()
    smr.project_id = project.id
    smr.survey_id = survey.id
    smr.membership_id = membership.id
    smr.role_id = role_in_other.id  # role belongs to other_project — mismatch
    db_session.add(smr)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(ForeignKeyViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "fk_survey_membership_roles_role_same_project", (
        f"Expected constraint 'fk_survey_membership_roles_role_same_project', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()
