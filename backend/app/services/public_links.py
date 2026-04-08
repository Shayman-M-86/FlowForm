from sqlalchemy.orm import Session

from app.db.transaction import commit_or_rollback
from app.domain import public_link_rules, survey_rules
from app.repositories import public_link_repo, surveys_repo
from app.schema.api.requests.public_links import CreatePublicLinkRequest, ResolveTokenRequest, UpdatePublicLinkRequest
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyPublicLink
from app.services.results import CreatePublicLinkResult, ResolveLinkResult


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
            survey=surveys_repo.get_published_version(db, survey_orm),
            survey_id=survey_id,
            project_id=project_id,
        )

        return ResolveLinkResult(
            link=link_orm,
            survey=survey_orm,
            published_version=published_version_orm,
        )

    def list_links(self, db: Session, project_id: int, survey_id: int) -> list[SurveyPublicLink]:
        """Lists all public links for a given survey."""
        self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        return list(public_link_repo.list_links(db, survey_id=survey_id))

    def create_link(
        self, db: Session, survey_id: int, project_id: int, data: CreatePublicLinkRequest
    ) -> CreatePublicLinkResult:
        """Creates a new public link for a survey."""
        self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        link, token = public_link_repo.create_link(
            db, survey_id=survey_id, allow_response=data.allow_response, expires_at=data.expires_at
        )
        commit_or_rollback(db)
        return CreatePublicLinkResult(link=link, token=token)

    def update_link(
        self,
        db: Session,
        *,
        survey_id: int,
        project_id: int,
        link_id: int,
        payload: UpdatePublicLinkRequest,
    ) -> SurveyPublicLink:
        """Updates an existing public link."""
        self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        link = self._get_link_invalidate(db, survey_id=survey_id, link_id=link_id)
        updated_link = public_link_repo.update_link(
            db,
            link=link,
            is_active=payload.is_active,
            allow_response=payload.allow_response,
            expires_at=payload.expires_at,
        )
        commit_or_rollback(db)

        return updated_link

    def delete_link(self, db: Session, *, survey_id: int, project_id: int, link_id: int) -> None:
        """Deletes a public link."""
        self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        link = self._get_link_invalidate(db, survey_id=survey_id, link_id=link_id)
        public_link_repo.delete_link(db, link=link)
        commit_or_rollback(db)

    def _ensure_survey_and_public_id_match(self, db: Session, survey_id: int, project_id: int) -> Survey:
        """Ensures that the survey ID and public link ID match."""
        return survey_rules.ensure_not_none(
            survey=surveys_repo.get_survey(db, project_id=project_id, survey_id=survey_id),
            survey_id=survey_id,
            project_id=project_id,
        )

    def _get_link_invalidate(self, db: Session, survey_id: int, link_id: int) -> SurveyPublicLink:
        """Ensures that a given public link belongs to the specified survey."""
        link = public_link_rules.ensure_is_not_none(
            link=public_link_repo.get_link(db, survey_id=survey_id, link_id=link_id)
        )
        return link
