"""Persistence of a document within the existing project/survey ownership chain."""

from sqlalchemy.orm import Session

from app.schema.api.content.survey_document import SurveyDefinition
from app.schema.orm.core.project import Project
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.user import User


def test_user_project_survey_document_chain(
    db_session: Session, user: User, project: Project, survey: Survey, survey_version: SurveyVersion
) -> None:
    db_session.refresh(survey_version)
    definition = SurveyDefinition.model_validate(survey_version.definition)
    assert definition.document.sections[0].blocks[0].type == "input"
    assert survey_version.survey.id == survey.id
    assert survey.project_id == project.id
    assert project.created_by_user_id == user.id
    assert survey_version.created_by_user_id == user.id
