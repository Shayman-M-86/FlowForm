from __future__ import annotations

import pytest
from psycopg.errors import CheckViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.schema.orm.core.project import Project
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_content import SurveyQuestion
from app.schema.orm.core.user import User
from tests.integration.core.factories import make_survey_question


def test_user_project_survey_questions_chain(
    db_session: scoped_session[Session],
    user: User,
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """
    A user creates a project, the project owns a survey, the survey has a
    version, and the version has questions. Assert the full chain is
    persisted and navigable.
    """
    q1 = make_survey_question(survey_version.id, question_key="q1", question_schema={"type": "field", "label": "Name"})
    q2 = make_survey_question(
        survey_version.id,
        question_key="q2",
        question_schema={"type": "choice", "label": "Colour", "options": ["red", "blue"]},
    )
    q3 = make_survey_question(
        survey_version.id, question_key="q3", question_schema={"type": "rating", "label": "Score", "max": 10}
    )

    db_session.add_all([q1, q2, q3])
    db_session.flush()

    # All questions got IDs
    assert q1.id is not None, "q1 was not persisted"
    assert q2.id is not None, "q2 was not persisted"
    assert q3.id is not None, "q3 was not persisted"

    # Questions are tied to the right survey version
    assert q1.survey_version_id == survey_version.id, (
        f"q1.survey_version_id={q1.survey_version_id!r}, expected {survey_version.id!r}"
    )
    assert q2.survey_version_id == survey_version.id, (
        f"q2.survey_version_id={q2.survey_version_id!r}, expected {survey_version.id!r}"
    )
    assert q3.survey_version_id == survey_version.id, (
        f"q3.survey_version_id={q3.survey_version_id!r}, expected {survey_version.id!r}"
    )

    # Survey version belongs to the survey
    assert survey_version.survey_id == survey.id, (
        f"survey_version.survey_id={survey_version.survey_id!r}, expected {survey.id!r}"
    )

    # Survey belongs to the project
    assert survey.project_id == project.id, (
        f"survey.project_id={survey.project_id!r}, expected {project.id!r}"
    )

    # Project was created by the user
    assert project.created_by_user_id == user.id, (
        f"project.created_by_user_id={project.created_by_user_id!r}, expected {user.id!r}"
    )

    # Navigate relationships: question → survey version → survey → creator
    db_session.refresh(q1)
    assert q1.survey_version.survey_id == survey.id, (
        f"q1.survey_version.survey_id={q1.survey_version.survey_id!r}, expected {survey.id!r}"
    )
    assert q1.survey_version.created_by_user_id == user.id, (
        f"q1.survey_version.created_by_user_id={q1.survey_version.created_by_user_id!r}, expected {user.id!r}"
    )

    # All three questions are retrievable for this survey version
    persisted = db_session.scalars(
        select(SurveyQuestion).where(SurveyQuestion.survey_version_id == survey_version.id)
    ).all()
    keys = {q.question_key for q in persisted}
    assert keys == {"q1", "q2", "q3"}, f"Expected questions {{q1, q2, q3}}, got {keys!r}"


@pytest.mark.parametrize("question_type", ["choice", "field", "matching", "rating"])
def test_survey_question_accepts_valid_type(
    db_session: scoped_session[Session],
    survey_version: SurveyVersion,
    question_type: str,
) -> None:
    """Each of the four known question types is accepted by the constraint."""
    question = make_survey_question(
        survey_version.id,
        question_key=question_type,
        question_schema={"type": question_type, "label": "Test"},
    )
    db_session.add(question)
    db_session.flush()
    assert question.id is not None, f"Question with type={question_type!r} was not persisted"


def test_survey_question_rejects_invalid_type(
    db_session: scoped_session[Session],
    survey_version: SurveyVersion,
) -> None:
    """question_schema->>'type' must be one of the four known question families."""
    bad = make_survey_question(
        survey_version.id,
        question_key="bad",
        question_schema={"type": "text", "label": "Unsupported"},
    )
    db_session.add(bad)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    assert isinstance(exc_info.value.orig, CheckViolation), (
        f"Expected CheckViolation, got {type(exc_info.value.orig).__name__}\n"
        f"DB error: {exc_info.value}"
    )
    constraint = exc_info.value.orig.diag.constraint_name
    assert constraint == "ck_survey_questions_question_type_valid", (
        f"Expected constraint 'ck_survey_questions_question_type_valid', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()
