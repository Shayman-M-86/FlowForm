from __future__ import annotations

from app.domain.errors import SurveyNotFoundError, SurveyNotPublishedError
from app.schema.orm.core.survey import Survey, SurveyVersion


def ensure_not_none(*, survey: Survey | None, survey_id: int, project_id: int) -> Survey:
    if survey is None:
        raise SurveyNotFoundError(survey_id=survey_id, project_id=project_id)
    return survey


def ensure_is_published(*, survey_version: SurveyVersion | None, survey_id: int, project_id: int) -> SurveyVersion:
    if not survey_version:
        raise SurveyNotPublishedError(survey_id=survey_id, project_id=project_id)
    return survey_version

