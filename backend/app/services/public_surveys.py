

from sqlalchemy.orm import Session

from app.domain import survey_rules
from app.repositories import surveys_repo
from app.services.results import GetPublicSurveyResult, ListPublicSurveysResult


class PublicSurveyService:
    """Service for fetching publicly accessible surveys by slug."""

    def list_public_surveys(self, db: Session, *, page: int, page_size: int) -> ListPublicSurveysResult:
        surveys, total = surveys_repo.list_public_surveys(db, page=page, page_size=page_size)
        return ListPublicSurveysResult(surveys=surveys, total=total, page=page, page_size=page_size)

    def get_public_survey(self, db: Session, *, public_slug: str) -> GetPublicSurveyResult:
        survey = survey_rules.ensure_found_by_slug(
            survey=surveys_repo.get_by_public_slug(db, public_slug)
        )
        published_version = surveys_repo.get_published_version(db, survey)
        return GetPublicSurveyResult(survey=survey, published_version=published_version)
