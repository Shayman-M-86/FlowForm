from app.domain import public_link_rules, survey_rules
from app.repositories import public_link_repo, surveys_repo
from app.schema.api.requests.submissions import ResolveTokenRequest
from app.schema.api.responses.public_links import PublicLinkOut, ResolveLinkOut
from app.schema.api.responses.surveys import SurveyOut, SurveyVersionOut
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyPublicLink
from sqlalchemy.orm import Session
from dataclasses import dataclass


@dataclass(slots=True)
class ResolveLinkResult:
    """Result of resolving a public link token."""
    link: SurveyPublicLink
    survey: Survey
    published_version: SurveyVersion

class PublicLinkService:
    """Service for handling operations related to public links."""
    def resolve_link(self, db: Session, *, payload: ResolveTokenRequest) -> ResolveLinkResult:
        """Resolves a public link token to its associated survey and published version.

        Ensures the link is valid and active.

        Raises:
            AppError: if the link is invalid, inactive, or expired.

        """
        link_orm: SurveyPublicLink = public_link_rules.ensure_is_not_none(
            link=public_link_repo.resolve_token(db, payload.token)
        )
        public_link_rules.ensure_is_active(link=link_orm)
        public_link_rules.ensure_not_expired(link=link_orm)

        project_id = link_orm.survey.project_id
        survey_id = link_orm.survey_id

        survey_orm: Survey = survey_rules.ensure_not_none(
            survey=surveys_repo.get_survey(db, project_id=project_id, survey_id=survey_id),
            survey_id=survey_id,
            project_id=project_id,
        )

        published_version_orm: SurveyVersion = survey_rules.ensure_is_published(
            survey_version=surveys_repo.get_published_version(db, survey_orm),
            survey_id=survey_id,
            project_id=project_id,
        )


        return ResolveLinkResult(
            link=link_orm,
            survey=survey_orm,
            published_version=published_version_orm,
        )
