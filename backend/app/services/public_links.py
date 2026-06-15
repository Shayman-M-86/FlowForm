from uuid import UUID

from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain import public_link_rules, submission_access_rules, survey_rules
from app.domain.errors import (
    LinkAuthAssignmentRequiredError,
    LinkNotFoundError,
    PrivateSurveyAssignedEmailRequiredError,
    SurveyNotFoundError,
)
from app.domain.guards import ensure_present
from app.repositories import public_link_repo as plr
from app.repositories import surveys_repo as sr
from app.repositories.core import project_participants as ppr
from app.schema.api.requests.public_links import CreatePublicLinkRequest, ResolveTokenRequest, UpdatePublicLinkRequest
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User
from app.services.participants import ParticipantService
from app.services.results import CreatePublicLinkResult, ResolveLinkResult

participant_service = ParticipantService()

class SurveyLinkService:
    """Service for handling operations related to survey links."""

    def verify_authenticated_link_participant(
        self,
        db: Session,
        *,
        payload: ResolveTokenRequest,
        actor: User,
    ) -> SurveyLink:
        """Verify this actor against an authenticated link's assigned participant."""
        link = ensure_present(
            plr.resolve_token(db, payload.token),
            error=LinkNotFoundError(),
        )
        public_link_rules.ensure_is_active(link=link)
        public_link_rules.ensure_not_expired(link=link)
        public_link_rules.ensure_not_used(link=link)

        if link.link_type != "authenticated":
            return link

        if link.assigned_participant_id is None:
            raise LinkAuthAssignmentRequiredError()

        participant = ensure_present(
            ppr.get_participant(
                db,
                project_id=link.project_id,
                participant_id=link.assigned_participant_id,
            ),
            error=LinkAuthAssignmentRequiredError(),
        )

        participant_service.verify_participant_for_user(
            db,
            participant=participant,
            user=actor,
        )
        return link

    def resolve_link(self, db: Session, payload: ResolveTokenRequest, actor: User | None) -> ResolveLinkResult:
        """Resolve a survey link token to its survey and published version.

        Authenticated links require a pre-verified participant identity whose
        user_id matches the authenticated actor.
        """
        link_orm: SurveyLink = ensure_present(
            plr.resolve_token(db, payload.token),
            error=LinkNotFoundError(),
        )
        project_id = link_orm.survey.project_id
        survey_id = link_orm.survey_id
        submission_access_rules.ensure_link_token_access(db, project_id=project_id, link=link_orm, actor=actor)

        survey_orm: Survey = ensure_present(
            sr.get_survey(db, project_id=project_id, survey_id=survey_id),
            error=SurveyNotFoundError(survey_id=survey_id, project_id=project_id),
        )

        published_version_orm: SurveyVersion = survey_rules.ensure_is_published(
            survey=sr.get_published_version(db, survey_orm),
            survey_id=survey_id,
            project_id=project_id,
        )

        return ResolveLinkResult(
            link=link_orm,
            survey=survey_orm,
            published_version=published_version_orm,
        )

    def list_links(self, db: Session, project_id: int, survey_id: int, actor: User) -> list[SurveyLink]:  # noqa: ARG002
        """List all links for a given survey."""
        self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        return list(plr.list_links(db, survey_id=survey_id))

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
        self._ensure_link_allowed_by_visibility(
            survey=survey,
            link_type=data.link_type,
            assigned_participant_id=data.assigned_participant_id,
        )
        link, token = plr.create_link(
            db,
            project_id=project_id,
            survey_id=survey_id,
            name=str(data.name),
            link_type=data.link_type,
            assignment_source=data.assignment_source,
            assigned_participant_id=data.assigned_participant_id,
            expires_at=data.expires_at,
        )
        commit_with_err_handle(db, contexts=[link])
        return CreatePublicLinkResult(link=link, token=token)

    def update_link(
        self,
        db: Session,
        survey_id: int,
        project_id: int,
        link_id: UUID,
        payload: UpdatePublicLinkRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyLink:
        """Update an existing survey link."""
        survey = self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        link = self._get_link_invalidate(db, survey_id=survey_id, link_id=link_id)
        next_link_type = payload.link_type if payload.link_type is not None else link.link_type
        next_assigned_participant_id = (
            payload.assigned_participant_id
            if "assigned_participant_id" in payload.model_fields_set
            else link.assigned_participant_id
        )
        self._ensure_link_allowed_by_visibility(
            survey=survey,
            link_type=next_link_type,
            assigned_participant_id=next_assigned_participant_id,
        )

        updated_link = plr.update_link(
            db,
            link=link,
            is_active=payload.is_active,
            name=payload.name,
            link_type=payload.link_type if payload.link_type is not None else plr.UNSET,
            assignment_source=(
                payload.assignment_source
                if payload.assignment_source is not None
                else plr.UNSET
            ),
            assigned_participant_id=(
                payload.assigned_participant_id
                if "assigned_participant_id" in payload.model_fields_set
                else plr.UNSET
            ),
            expires_at=(
                payload.expires_at
                if "expires_at" in payload.model_fields_set
                else plr.UNSET
            ),
        )
        commit_with_err_handle(db, contexts=[updated_link])

        return updated_link

    def delete_link(self, db: Session, survey_id: int, project_id: int, link_id: UUID, actor: User) -> None:  # noqa: ARG002
        """Delete a survey link."""
        self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        link = self._get_link_invalidate(db, survey_id=survey_id, link_id=link_id)
        plr.delete_link(db, link=link)
        commit_with_err_handle(db, contexts=[link])

    def _ensure_survey_and_public_id_match(self, db: Session, survey_id: int, project_id: int) -> Survey:
        """Ensure that the survey ID and link ID match."""
        return ensure_present(
            sr.get_survey(db, project_id=project_id, survey_id=survey_id),
            error=SurveyNotFoundError(survey_id=survey_id, project_id=project_id),
        )

    def _get_link_invalidate(self, db: Session, survey_id: int, link_id: UUID) -> SurveyLink:
        """Ensure that a given link belongs to the specified survey."""
        link = ensure_present(
            plr.get_link(db, survey_id=survey_id, link_id=link_id),
            error=LinkNotFoundError(),
        )
        return link

    def _ensure_link_allowed_by_visibility(
        self,
        *,
        survey: Survey,
        link_type: str,
        assigned_participant_id: UUID | None,
    ) -> None:
        """Validate that a link's auth/assignment fits the survey's visibility.

        General links are reusable and unassigned. Private/authenticated links
        are participant-assigned and single-use.
        """
        if link_type == "general" and assigned_participant_id is not None:
            raise LinkAuthAssignmentRequiredError()

        if link_type != "general" and assigned_participant_id is None:
            raise LinkAuthAssignmentRequiredError()

        if survey.visibility == "private" and link_type == "general":
            raise PrivateSurveyAssignedEmailRequiredError()


PublicLinkService = SurveyLinkService
