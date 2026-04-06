

from sqlalchemy.orm import Session

from app.domain import survey_rules
from app.repositories import surveys_repo
from app.services.results import GetPublicSurveyResult


class PublicSurveyService:
    """Service for fetching publicly accessible surveys by slug."""

    def get_public_survey(self, db: Session, *, public_slug: str) -> GetPublicSurveyResult:
        survey = survey_rules.ensure_found_by_slug(
            survey=surveys_repo.get_by_public_slug(db, public_slug)
        )
        published_version = surveys_repo.get_published_version(db, survey)
        return GetPublicSurveyResult(survey=survey, published_version=published_version)
