"""Respondent-facing survey resolution: public slug browsing and link token resolution.

API-facing entry point. Routes in api/v1/public.py call this service directly.
Delegates access-method logic to core/access_resolver.py.

Docs: docs/Policies and Services/service-structure.md
      docs/Policies and Services/Flows/Public-slug-flow.md
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain import public_link_rules
from app.domain.errors import (
    LinkAuthAssignmentRequiredError,
    LinkNotFoundError,
    SurveyNotFoundBySlugError,
)
from app.domain.guards import ensure_present
from app.repositories import public_link_repo as plr
from app.repositories import surveys_repo as sr
from app.repositories.core import project_participants as ppr
from app.schema.api.requests.public_links import ResolveTokenRequest
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User
from app.services.participants import ParticipantService
from app.services.public_submissions.core.access_resolver import AccessResolver
from app.services.results import (
    GetPublicSurveyResult,
    ListPublicSurveysResult,
    ResolveLinkResult,
)


class SurveyResolveService:
    """Respondent-facing survey resolution: slug browsing and link token resolution."""

    def __init__(
        self,
        *,
        access_resolver: AccessResolver | None = None,
        participant_service: ParticipantService | None = None,
    ) -> None:
        self._access_resolver = access_resolver or AccessResolver()
        self._participant_service = participant_service or ParticipantService()

    # ------------------------------------------------------------------
    # Public slug — browsing (unauthenticated)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Link token — resolution
    # ------------------------------------------------------------------

    def resolve_link(
        self,
        db: Session,
        payload: ResolveTokenRequest,
        actor: User | None,
    ) -> ResolveLinkResult:
        """Resolve a survey link token to its survey and published version.

        Authenticated links require a pre-verified participant identity whose
        user_id matches the authenticated actor.
        Docs: shared/resolve-link-token.md
        """
        link = ensure_present(plr.resolve_token(db, payload.token), error=LinkNotFoundError())
        grant = self._access_resolver.resolve_link_token(db, link=link, actor=actor)
        return ResolveLinkResult(
            link=link,
            survey=grant.survey,
            published_version=grant.published_version,
        )

    def verify_authenticated_link_participant(
        self,
        db: Session,
        *,
        payload: ResolveTokenRequest,
        actor: User,
    ) -> SurveyLink:
        """Verify this actor against an authenticated link's assigned participant."""
        link = ensure_present(plr.resolve_token(db, payload.token), error=LinkNotFoundError())
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
        self._participant_service.verify_participant_for_user(db, participant=participant, user=actor)
        return link
