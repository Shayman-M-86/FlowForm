from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import current_settings
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import (
    LinkAuthAssignmentRequiredError,
    LinkNoRecipientError,
    LinkNotFoundError,
    PrivateSurveyAssignedEmailRequiredError,
    SurveyNotFoundError,
)
from app.domain.guards import ensure_present
from app.email_service import get_email_service
from app.repositories import public_link_repo as plr
from app.repositories import surveys_repo as sr
from app.schema.api.requests.survey_access_links import CreateSurveyAccessLinkRequest, UpdateSurveyAccessLinkRequest
from app.schema.orm.core.survey import Survey
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User


class SurveyLinkService:
    """Admin-facing survey link management: list, create, update, delete."""

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
        data: CreateSurveyAccessLinkRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyLink:
        """Create a new link for a survey."""
        survey = self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        self._ensure_link_allowed_by_visibility(
            survey=survey,
            link_type=data.link_type,
            assigned_participant_id=data.assigned_participant_id,
        )
        link = plr.create_link(
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
        return link

    def update_link(
        self,
        db: Session,
        survey_id: int,
        project_id: int,
        link_id: UUID,
        payload: UpdateSurveyAccessLinkRequest,
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
            assignment_source=(payload.assignment_source if payload.assignment_source is not None else plr.UNSET),
            assigned_participant_id=(
                payload.assigned_participant_id if "assigned_participant_id" in payload.model_fields_set else plr.UNSET
            ),
            expires_at=(payload.expires_at if "expires_at" in payload.model_fields_set else plr.UNSET),
        )
        commit_with_err_handle(db, contexts=[updated_link])

        return updated_link

    def delete_link(self, db: Session, survey_id: int, project_id: int, link_id: UUID, actor: User) -> None:  # noqa: ARG002
        """Delete a survey link."""
        self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        link = self._get_link_invalidate(db, survey_id=survey_id, link_id=link_id)
        plr.delete_link(db, link=link)
        commit_with_err_handle(db, contexts=[link])

    def send_link_email(
        self,
        db: Session,
        survey_id: int,
        project_id: int,
        link_id: UUID,
        actor: User,  # noqa: ARG002
    ) -> str | None:
        """Send a survey invite email for an existing link."""
        survey = self._ensure_survey_and_public_id_match(db, survey_id=survey_id, project_id=project_id)
        link = self._get_link_invalidate(db, survey_id=survey_id, link_id=link_id)

        if link.assigned_participant is None:
            raise LinkNoRecipientError()

        recipient_email = link.assigned_participant.identity.normalized_email
        if not recipient_email:
            raise LinkNoRecipientError()

        site_url = current_settings().flowform.server.site_url.rstrip("/")
        survey_url = f"{site_url}/respond/{link.token}"

        message_id = get_email_service().send_survey_invite({
            "to_email": recipient_email,
            "survey_name": survey.title,
            "survey_url": survey_url,
            "expires_at": link.expires_at,
        })

        link.emailed_at = datetime.now(UTC)
        commit_with_err_handle(db)

        return message_id

    def _ensure_survey_and_public_id_match(self, db: Session, survey_id: int, project_id: int) -> Survey:
        return ensure_present(
            sr.get_survey(db, project_id=project_id, survey_id=survey_id),
            error=SurveyNotFoundError(survey_id=survey_id, project_id=project_id),
        )

    def _get_link_invalidate(self, db: Session, survey_id: int, link_id: UUID) -> SurveyLink:
        return ensure_present(
            plr.get_link(db, survey_id=survey_id, link_id=link_id),
            error=LinkNotFoundError(),
        )

    def _ensure_link_allowed_by_visibility(
        self,
        *,
        survey: Survey,
        link_type: str,
        assigned_participant_id: UUID | None,
    ) -> None:
        """Write-time check: validate that the link type and assignment fit the survey's visibility."""
        if link_type == "general" and assigned_participant_id is not None:
            raise LinkAuthAssignmentRequiredError()

        if link_type != "general" and assigned_participant_id is None:
            raise LinkAuthAssignmentRequiredError()

        if survey.visibility == "private" and link_type == "general":
            raise PrivateSurveyAssignedEmailRequiredError()
