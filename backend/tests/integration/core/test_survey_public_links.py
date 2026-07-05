from __future__ import annotations

from typing import cast

import pytest  # type: ignore[import]
from psycopg.errors import NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schema.orm.core.survey import Survey
from app.schema.orm.core.survey_access import SurveyLink
from tests.integration.core.factories import make_token


def test_survey_public_link_can_be_created(
    db_session: Session, survey: Survey
) -> None:
    """All fields are persisted and server defaults populate is_active and created_at."""
    token = make_token()

    link = SurveyLink()
    link.project_id = survey.project_id
    link.survey_id = survey.id
    link.name = "test link"
    link.token = token
    link.assignment_source = "manual"
    db_session.add(link)
    db_session.flush()

    saved = db_session.get(SurveyLink, link.id)
    assert saved is not None, "SurveyLink was not persisted"
    assert saved.survey_id == survey.id, f"survey_id={saved.survey_id!r}, expected {survey.id!r}"
    assert saved.name == "test link", f"name={saved.name!r}, expected 'test link'"
    assert saved.token == token, f"token={saved.token!r}, expected {token!r}"
    assert saved.is_active is True, f"is_active={saved.is_active!r}, expected True from server default"
    assert saved.link_type == "general", f"link_type={saved.link_type!r}, expected 'general'"
    assert saved.assignment_source == "manual", f"assignment_source={saved.assignment_source!r}, expected 'manual'"
    assert saved.assigned_participant_id is None, (
        f"assigned_participant_id={saved.assigned_participant_id!r}, expected None"
    )
    assert saved.expires_at is None, f"expires_at={saved.expires_at!r}, expected None"
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_survey_public_link_unique_token(
    db_session: Session, survey: Survey
) -> None:
    """token must be globally unique — two links cannot share the same token."""
    token = make_token()

    link_a = SurveyLink()
    link_a.project_id = survey.project_id
    link_a.survey_id = survey.id
    link_a.name = "link a"
    link_a.token = token
    link_a.assignment_source = "manual"
    db_session.add(link_a)
    db_session.flush()

    link_b = SurveyLink()
    link_b.project_id = survey.project_id
    link_b.survey_id = survey.id
    link_b.name = "link b"
    link_b.token = token
    link_b.assignment_source = "manual"
    db_session.add(link_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_survey_links_token", (
        f"Expected constraint 'uq_survey_links_token', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_public_link_requires_token(
    db_session: Session, survey: Survey
) -> None:
    """token is NOT NULL — omitting it raises an IntegrityError."""
    link = SurveyLink()
    link.project_id = survey.project_id
    link.survey_id = survey.id
    link.name = "test link"
    link.token = None  # type: ignore[assignment]
    link.assignment_source = "manual"
    db_session.add(link)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "token", (
        f"Expected NOT NULL violation on 'token', got '{column}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_public_link_cascades_on_survey_delete(
    db_session: Session, survey: Survey
) -> None:
    """Deleting the survey removes all its public links."""
    link = SurveyLink()
    link.project_id = survey.project_id
    link.survey_id = survey.id
    link.name = "test link"
    link.token = make_token()
    link.assignment_source = "manual"
    db_session.add(link)
    db_session.flush()

    link_id = link.id
    db_session.delete(survey)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(SurveyLink, link_id) is None, (
        "SurveyLink should have been deleted when its survey was deleted"
    )
