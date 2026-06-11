

from sqlalchemy.orm import Session

from app.domain.errors import SurveyNotFoundBySlugError
from app.domain.guards import ensure_present
from app.repositories import surveys_repo as sr
from app.services.results import GetPublicSurveyResult, ListPublicSurveysResult


class PublicSurveyService:
    """Service for fetching publicly accessible surveys by slug."""

    def list_public_surveys(self, db: Session, *, page: int, page_size: int) -> ListPublicSurveysResult:
        surveys, total = sr.list_public_surveys(db, page=page, page_size=page_size)
        return ListPublicSurveysResult(surveys=surveys, total=total, page=page, page_size=page_size)

    def get_public_survey(self, db: Session, *, public_slug: str) -> GetPublicSurveyResult:
        survey = ensure_present(
            sr.get_by_public_slug(db, public_slug),
            error=SurveyNotFoundBySlugError(),
        )
        published_version = sr.get_published_version(db, survey)
        return GetPublicSurveyResult(survey=survey, published_version=published_version)
