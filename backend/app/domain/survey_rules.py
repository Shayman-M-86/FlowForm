from __future__ import annotations

from pydantic import TypeAdapter, ValidationError

from app.domain.errors import (
    SurveyNoResponseStoreError,
    SurveyNotAccessibleError,
    SurveyNotPublishedError,
    SurveyVisibilityMismatchError,
)
from app.schema.enums import SurveyVisibility
from app.schema.models.common.survey_access import SurveyAccess
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.types import ProjectId, ResponseStoreId, Slug, SurveyId

_ACCESS = TypeAdapter(SurveyAccess)


def ensure_is_published(
    *, survey: SurveyVersion | None | Survey, survey_id: SurveyId, project_id: ProjectId
) -> SurveyVersion:
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


def ensure_has_response_store(*, survey: Survey) -> ResponseStoreId:
    if survey.default_response_store_id is None:
        raise SurveyNoResponseStoreError(message=f"Survey {survey.id} has no default response store configured")
    return survey.default_response_store_id


def ensure_default_response_store(
    *,
    survey: Survey,
    default_response_store_id: ResponseStoreId,
) -> ResponseStoreId:
    if survey.default_response_store_id is None:
        survey.default_response_store_id = default_response_store_id
    return survey.default_response_store_id


def ensure_visibility_slug_coherent(*, visibility: SurveyVisibility, public_slug: Slug | None) -> None:
    """Validate merged update metadata with the same variants used by requests."""
    try:
        _ACCESS.validate_python({"visibility": visibility, "public_slug": public_slug})
    except ValidationError as exc:
        raise SurveyVisibilityMismatchError("Survey visibility and public slug are inconsistent.") from exc
