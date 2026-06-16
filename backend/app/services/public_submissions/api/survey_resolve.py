"""Respondent-facing survey resolution: slug browsing, link resolution, and account linking.

API-facing entry point. Routes in api/v1/public.py call this service directly.
Delegates access-method logic to core/access_resolver.py.

Docs: docs/Policies and Services/service-structure.md
      docs/Policies and Services/Flows/Public-slug-flow.md
      docs/Policies and Services/Flows/Authenticated-link-access-Flow.md
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain import public_link_rules
from app.domain.errors import (
    LinkAuthAssignmentRequiredError,
    LinkAuthRequiredError,
    LinkNotFoundError,
    SurveyNotFoundBySlugError,
)
from app.domain.guards import ensure_present
from app.repositories import public_link_repo as plr
from app.repositories import surveys_repo as sr
from app.repositories.core import project_participants as ppr
from app.repositories.core import project_subjects as subjects
from app.schema.api.requests.public_links import ResolveTokenRequest
from app.schema.orm.core.user import User
from app.services.participants import ParticipantService
from app.services.public_submissions.core.access_resolver import AccessResolver
from app.services.public_submissions.core.subject_resolver import SubjectResolver
from app.services.public_submissions.core.subject_token import SubjectTokenService
from app.services.results import (
    AccountLinkingResult,
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
        subject_resolver: SubjectResolver | None = None,
        token_service: SubjectTokenService | None = None,
    ) -> None:
        self._access_resolver = access_resolver or AccessResolver()
        self._participant_service = participant_service or ParticipantService()
        self._subject_resolver = subject_resolver or SubjectResolver()
        self._token_service = token_service or SubjectTokenService()

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
        recognition_token: str | None,
    ) -> AccountLinkingResult:
        """Link the assigned participant identity to the logged-in user and reconcile token.

        Validates that the link is of type authenticated, the assigned identity email
        matches the logged-in user's email, then links the identity. After linking,
        reconciles the browser recognition token against the now-authoritative assigned
        subject using assigned-access subject resolution.

        Returns the raw recognition token only when rotation was required so the caller
        can update the browser cookie. None means the cookie is unchanged.

        Docs: Authenticated-link-access-Flow.md §5
        """
        link = ensure_present(plr.resolve_token(db, payload.token), error=LinkNotFoundError())
        public_link_rules.ensure_is_active(link=link)
        public_link_rules.ensure_not_expired(link=link)
        public_link_rules.ensure_not_used(link=link)

        if link.link_type != "authenticated":
            raise LinkAuthRequiredError()

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

        # Reconcile browser recognition token against assigned subject.
        # Docs: Authenticated-link-access-Flow.md §5 — Recognition token reconciliation
        token_lookup = (
            self._token_service.lookup(db, project_id=link.project_id, raw_token=recognition_token)
            if recognition_token is not None
            else None
        )
        token_subject_id = token_lookup.token_subject_id if (token_lookup and token_lookup.token_valid) else None
        canonical_token_subject_id = (
            token_lookup.canonical_token_subject_id if (token_lookup and token_lookup.token_valid) else None
        )

        resolution = self._subject_resolver.resolve_assigned_subject(
            db,
            project_id=link.project_id,
            assigned_subject_id=participant.project_subject_id,
            token_subject_id=token_subject_id,
            canonical_token_subject_id=canonical_token_subject_id,
        )

        # Apply merge if token subject differs from assigned subject.
        if resolution.merge_subject_id is not None and resolution.merge_into_subject_id is not None:
            weaker = subjects.get_subject(
                db, project_id=link.project_id, subject_id=resolution.merge_subject_id
            )
            stronger = subjects.get_subject(
                db, project_id=link.project_id, subject_id=resolution.merge_into_subject_id
            )
            if weaker is not None and stronger is not None:
                subjects.set_canonical_subject(db, subject=weaker, canonical=stronger)

        raw_recognition_token = self._token_service.apply_token_action(
            db,
            project_id=link.project_id,
            final_subject_id=resolution.final_subject_id,
            token_action=resolution.token_action,
            existing_raw_token=recognition_token,
        )

        # Only return the token when the cookie must change (issue or rotate).
        new_token = raw_recognition_token if resolution.token_action in ("issue", "rotate") else None
        return AccountLinkingResult(link=link, raw_recognition_token=new_token)
