from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain import public_link_rules, survey_rules
from app.domain.errors import (
    NonPrivateSurveyAssignedEmailForbiddenError,
    PrivateSurveyAssignedEmailRequiredError,
)
from app.domain.permissions import PERMISSIONS
from app.repositories import public_link_repo, surveys_repo
from app.schema.api.requests.public_links import CreatePublicLinkRequest, ResolveTokenRequest, UpdatePublicLinkRequest
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User
from app.services.access.access_service import require_survey_permission
from app.services.results import CreatePublicLinkResult, ResolveLinkResult


class SurveyLinkService:
    """Service for handling operations related to survey links."""

    def resolve_link(self, db: Session, payload: ResolveTokenRequest, actor: User) -> ResolveLinkResult:
        """Resolve a survey link token to its survey and published version.

        The actor must be authenticated. If the link is assigned to an email,
        that email must match the authenticated user.
        """
        link_orm: SurveyLink = public_link_rules.ensure_is_not_none(
            link=public_link_repo.resolve_token(db, payload.token)
        )
        public_link_rules.ensure_is_active(link=link_orm)
        public_link_rules.ensure_not_expired(link=link_orm)
        public_link_rules.ensure_actor_matches_assignment(link=link_orm, actor_email=actor.email)

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

    @require_survey_permission(PERMISSIONS.survey.view)
    def list_links(self, db: Session, project_id: int, survey_id: int, actor: User) -> list[SurveyLink]:  # noqa: ARG002
        """List all links for a given survey."""
        self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        return list(public_link_repo.list_links(db, survey_id=survey_id))

    @require_survey_permission(PERMISSIONS.survey.edit)
    def create_link(
        self,
        db: Session,
        *,
        survey_id: int,
        project_id: int,
        data: CreatePublicLinkRequest,
        actor: User,  # noqa: ARG002
    ) -> CreatePublicLinkResult:
        """Create a new link for a survey."""
        survey = self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        self._ensure_assignment_matches_visibility(survey=survey, assigned_email=data.assigned_email)
        link, token = public_link_repo.create_link(
            db,
            survey_id=survey_id,
            assigned_email=data.assigned_email,
            expires_at=data.expires_at,
        )
        commit_with_err_handle(db, contexts=[link])
        return CreatePublicLinkResult(link=link, token=token)

    @require_survey_permission(PERMISSIONS.survey.edit)
    def update_link(
        self,
        db: Session,
        survey_id: int,
        project_id: int,
        link_id: int,
        payload: UpdatePublicLinkRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyLink:
        """Update an existing survey link."""
        survey = self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        link = self._get_link_invalidate(db, survey_id=survey_id, link_id=link_id)
        next_assigned_email = link.assigned_email
        if "assigned_email" in payload.model_fields_set:
            next_assigned_email = payload.assigned_email
        self._ensure_assignment_matches_visibility(survey=survey, assigned_email=next_assigned_email)

        updated_link = public_link_repo.update_link(
            db,
            link=link,
            is_active=payload.is_active,
            assigned_email=(
                payload.assigned_email
                if "assigned_email" in payload.model_fields_set
                else public_link_repo.UNSET
            ),
            expires_at=payload.expires_at,
        )
        commit_with_err_handle(db, contexts=[updated_link])

        return updated_link

    @require_survey_permission(PERMISSIONS.survey.edit)
    def delete_link(self, db: Session, survey_id: int, project_id: int, link_id: int, actor: User) -> None:  # noqa: ARG002
        """Delete a survey link."""
        self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        link = self._get_link_invalidate(db, survey_id=survey_id, link_id=link_id)
        public_link_repo.delete_link(db, link=link)
        commit_with_err_handle(db, contexts=[link])

    def _ensure_survey_and_public_id_match(self, db: Session, survey_id: int, project_id: int) -> Survey:
        """Ensure that the survey ID and link ID match."""
        return survey_rules.ensure_not_none(
            survey=surveys_repo.get_survey(db, project_id=project_id, survey_id=survey_id),
            survey_id=survey_id,
            project_id=project_id,
        )

    def _get_link_invalidate(self, db: Session, survey_id: int, link_id: int) -> SurveyLink:
        """Ensure that a given link belongs to the specified survey."""
        link = public_link_rules.ensure_is_not_none(
            link=public_link_repo.get_link(db, survey_id=survey_id, link_id=link_id)
        )
        return link

    def _ensure_assignment_matches_visibility(self, *, survey: Survey, assigned_email: str | None) -> None:
        if survey.visibility == "private" and assigned_email is None:
            raise PrivateSurveyAssignedEmailRequiredError()
        if survey.visibility != "private" and assigned_email is not None:
            raise NonPrivateSurveyAssignedEmailForbiddenError()


PublicLinkService = SurveyLinkService
