"""Persist a complete survey definition through the project ownership chain."""

from sqlalchemy.orm import Session

from app.repositories import surveys_repo
from app.schema.models.survey_document.document import InputBlock
from app.schema.orm.core import Project, Survey, SurveyVersion, User
from tests.integration.core.factories import define_version


def test_user_project_survey_document_chain(
    db_session: Session,
    user: User,
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    definition = define_version(db_session, survey_version, field_ids=("name", "colour", "score"))
    db_session.flush()
    db_session.expire(survey_version)

    assert survey_version.survey is survey
    assert survey_version.created_by is user
    assert survey.project_id == project.id
    assert project.created_by is user

    stored = surveys_repo.get_content(db_session, project.id, survey.id, survey_version.version_number)
    assert stored == definition
    assert stored is not None
    fields = [
        block.field.id for section in stored.sections for block in section.blocks if isinstance(block, InputBlock)
    ]
    assert fields == ["name", "colour", "score"]
