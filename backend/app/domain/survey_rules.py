from __future__ import annotations

from app.domain.errors import (
    SurveyNoResponseStoreError,
    SurveyNotFoundBySlugError,
    SurveyNotFoundError,
    SurveyNotPublishedError,
)
from app.schema.orm.core.survey import Survey, SurveyVersion


def ensure_not_none(*, survey: Survey | None, survey_id: int, project_id: int) -> Survey:
    if survey is None:
        raise SurveyNotFoundError(survey_id=survey_id, project_id=project_id)
    return survey


def ensure_is_published(
    *, survey: SurveyVersion | None | Survey, survey_id: int, project_id: int
) -> SurveyVersion:
    if not survey:
        raise SurveyNotPublishedError(survey_id=survey_id, project_id=project_id)
    if isinstance(survey, Survey):
        survey = survey.published_version
    if survey is None or survey.status != "published":
        raise SurveyNotPublishedError(survey_id=survey_id, project_id=project_id)
    return survey


def ensure_found_by_slug(*, survey: Survey | None) -> Survey:
    if survey is None:
        raise SurveyNotFoundBySlugError()
    return survey


def ensure_has_response_store(*, survey: Survey) -> int:
    if survey.default_response_store_id is None:
        raise SurveyNoResponseStoreError()
    return survey.default_response_store_id


def ensure_survey_belongs_to_project(*, survey_id: int, project_surveys_ids: list[int], project_id: int) -> None:
    if survey_id not in project_surveys_ids:
            raise SurveyNotFoundError(survey_id=survey_id, project_id=project_id)