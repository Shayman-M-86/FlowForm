from __future__ import annotations

from app.domain.errors import (
    SurveyNoResponseStoreError,
    SurveyNotAccessibleError,
    SurveyNotFoundError,
    SurveyNotPublishedError,
    SurveyVisibilityMismatchError,
)
from app.schema.orm.core.survey import Survey, SurveyVersion


def ensure_is_published(*, survey: SurveyVersion | None | Survey, survey_id: int, project_id: int) -> SurveyVersion:
    if not survey:
        raise SurveyNotPublishedError(survey_id=survey_id, project_id=project_id)
    if isinstance(survey, Survey):
        survey = survey.published_version
    if survey is None or survey.status != "published":
        raise SurveyNotPublishedError(survey_id=survey_id, project_id=project_id)
    return survey


def ensure_is_publicly_accessible(*, survey: Survey) -> Survey:
    """Raise if the survey is not publicly browsable."""
    if survey.visibility != "public":
        raise SurveyNotAccessibleError()
    return survey


def ensure_has_response_store(*, survey: Survey) -> int:
    if survey.default_response_store_id is None:
        raise SurveyNoResponseStoreError(message=f"Survey {survey.id} has no default response store configured")
    return survey.default_response_store_id


def ensure_survey_belongs_to_project(*, survey_id: int, project_surveys_ids: list[int], project_id: int) -> None:
    if survey_id not in project_surveys_ids:
        raise SurveyNotFoundError(survey_id=survey_id, project_id=project_id)


def ensure_default_response_store(
    *,
    survey: Survey,
    default_response_store_id: int,
) -> int:
    if survey.default_response_store_id is None:
        survey.default_response_store_id = default_response_store_id
    return survey.default_response_store_id


def ensure_visibility_slug_coherent(*, visibility: str, public_slug: str | None) -> None:
    """Validate that ``visibility`` and ``public_slug`` form a coherent pair.

    Mirrors the database CHECK constraints ``ck_surveys_public_requires_slug``
    and ``ck_surveys_slug_requires_public_visibility``. Call this before any
    write that may change either field so the request fails fast with a clean
    422 instead of tripping the CHECK at COMMIT time.
    """
    if visibility == "public" and not public_slug:
        raise SurveyVisibilityMismatchError("public_slug is required when visibility is 'public'.")
    if public_slug and visibility != "public":
        raise SurveyVisibilityMismatchError("public_slug requires visibility 'public'.")


def ensure_can_delete_survey(survey: Survey) -> None:
    if survey.published_version_id is not None:
        pass
        # raise SurveyDeletePublishedError(survey_id=survey.id)
