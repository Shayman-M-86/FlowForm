"""Resolve respondent access to a survey via public slug or link token.

Docs: docs/Policies and Services/Flows/Public-slug-flow.md
      docs/Policies and Services/Flows/General-Link-Flow.md
      docs/Policies and Services/Flows/Private-link-access-Flow.md
      docs/Policies and Services/Flows/Authenticated-link-access-Flow.md
      docs/Policies and Services/Flows/shared/resolve-link-token.md
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain import submission_access_rules, survey_rules
from app.domain.errors import LinkNotFoundError, SurveyNotFoundBySlugError, SurveyNotFoundError
from app.domain.guards import ensure_present
from app.repositories import public_link_repo as plr
from app.repositories import surveys_repo as sr
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User
from app.services.results import SubmissionAccessGrant, SubmissionAccessMethod

_LINK_ACCESS_METHODS: dict[str, SubmissionAccessMethod] = {
    "general": "general_link",
    "private": "private_link",
    "authenticated": "authenticated_assigned_link",
}


class AccessResolver:
    """Resolve public-slug or link-token access into a validated SubmissionAccessGrant.

    Shared entry point for both survey resolve (preview) and session start.
    Does NOT resolve subject or token — that is SubjectResolver's job.

    ``resolve()`` routes on ``access.type`` and guarantees every returned
    ``SubmissionAccessGrant`` has passed **all** of the following checks:

    Common (both paths):
      1. Survey exists — raises SurveyNotFoundBySlugError / SurveyNotFoundError.
      2. Survey has a published version with status="published"
         — raises SurveyNotPublishedError.
      3. Survey has a default response store configured
         — raises SurveyNoResponseStoreError.

    Public-slug path (``access.type == "public_slug"``):
      3. Survey visibility is "public" — raises SurveyNotAccessibleError.

    Link-token path (``access.type != "public_slug"``):
      3. Link token resolves to a SurveyLink row — raises LinkNotFoundError.
      4. Link is active (``is_active=True``) — raises LinkInactiveError.
      5. Link is not expired (``expires_at`` is null or in the future)
         — raises LinkExpiredError.
      6. Authenticated links require a logged-in actor
         — raises LinkAuthRequiredError.
      7. Single-use links have not already been used (``used_at`` is null)
         — raises LinkAlreadyUsedError.
      8. General links cannot access private-visibility surveys
         — raises PrivateSurveyAssignedEmailRequiredError.

    Authenticated-link extras (actor is present and ``link_type == "authenticated"``):
      9.  Link has an assigned participant — raises LinkAuthAssignmentRequiredError.
      10. Participant exists in the project — raises LinkAuthAssignmentRequiredError.
      11. Participant identity is type "authenticated_user" with a linked user_id
          — raises LinkParticipantVerificationRequiredError.
      12. Actor matches the participant identity's user_id
          — raises LinkAssignmentMismatchError.
    """

    def resolve(
        self,
        db: Session,
        *,
        payload: StartSubmissionSessionRequest,
        actor: User | None,
    ) -> SubmissionAccessGrant:
        """Route to public-slug or link-token resolution based on access type."""
        access = payload.access
        if access.type == "public_slug":
            return self.resolve_public_slug(db, public_slug=access.public_slug)

        link = ensure_present(plr.resolve_token(db, access.token), error=LinkNotFoundError())
        return self.resolve_link_token(db, link=link, actor=actor)

    def resolve_public_slug(self, db: Session, *, public_slug: str) -> SubmissionAccessGrant:
        """Validate slug, check visibility=public, check published version.

        Docs: Public-slug-flow.md §1
        """
        survey = ensure_present(
            sr.get_by_public_slug(db, public_slug=public_slug),
            error=SurveyNotFoundBySlugError(),
        )
        survey_rules.ensure_is_publicly_accessible(survey=survey)
        published_version = survey_rules.ensure_is_published(
            survey=sr.get_published_version(db, survey),
            survey_id=survey.id,
            project_id=survey.project_id,
        )
        response_store_id = survey_rules.ensure_has_response_store(survey=survey)
        return SubmissionAccessGrant(
            access_method="public_slug",
            project_id=survey.project_id,
            survey_id=survey.id,
            survey_version_id=published_version.id,
            response_store_id=response_store_id,
            link_id=None,
            assigned_subject_id=None,
            requires_auth=False,
            is_single_use=False,
            survey=survey,
            published_version=published_version,
            link=None,
        )

    def resolve_link_token(
        self,
        db: Session,
        *,
        link: SurveyLink,
        actor: User | None,
    ) -> SubmissionAccessGrant:
        """Run all link state checks, fetch survey, check published version.

        Shared by General, Private, Authenticated flows.
        Docs: shared/resolve-link-token.md
        """
        survey = ensure_present(
            sr.get_survey(db, project_id=link.project_id, survey_id=link.survey_id),
            error=SurveyNotFoundError(survey_id=link.survey_id, project_id=link.project_id),
        )
        submission_access_rules.ensure_link_token_access(
            db, project_id=link.project_id, link=link, survey=survey, actor=actor
        )
        published_version = survey_rules.ensure_is_published(
            survey=sr.get_published_version(db, survey),
            survey_id=survey.id,
            project_id=survey.project_id,
        )
        response_store_id = survey_rules.ensure_has_response_store(survey=survey)
        assigned_subject_id = (
            link.assigned_participant.project_subject_id
            if link.assigned_participant is not None
            else None
        )
        return SubmissionAccessGrant(
            access_method=_LINK_ACCESS_METHODS[link.link_type],
            project_id=survey.project_id,
            survey_id=survey.id,
            survey_version_id=published_version.id,
            response_store_id=response_store_id,
            link_id=link.id,
            assigned_subject_id=assigned_subject_id,
            requires_auth=link.link_type == "authenticated",
            is_single_use=link.is_single_use,
            survey=survey,
            published_version=published_version,
            link=link,
        )
