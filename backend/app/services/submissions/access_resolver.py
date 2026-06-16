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


class SurveyAccessResolver:
    """Resolve public-slug or link-token access for respondent session starts."""

    def resolve(
        self,
        db: Session,
        *,
        payload: StartSubmissionSessionRequest,
        actor: User | None,
    ) -> SubmissionAccessGrant:
        access = payload.access
        if access.type == "public_slug":
            return self._resolve_public_slug(db, public_slug=access.public_slug)

        link = ensure_present(plr.resolve_token(db, access.token), error=LinkNotFoundError())
        return self._resolve_link(db, link=link, actor=actor)

    def _resolve_public_slug(self, db: Session, *, public_slug: str) -> SubmissionAccessGrant:
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
        return SubmissionAccessGrant(
            access_method="public_slug",
            project_id=survey.project_id,
            survey_id=survey.id,
            survey_version_id=published_version.id,
            link_id=None,
            assigned_subject_id=None,
            requires_auth=False,
            is_single_use=False,
            survey=survey,
            published_version=published_version,
            link=None,
        )

    def _resolve_link(self, db: Session, *, link: SurveyLink, actor: User | None) -> SubmissionAccessGrant:
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
            link_id=link.id,
            assigned_subject_id=assigned_subject_id,
            requires_auth=link.link_type == "authenticated",
            is_single_use=link.is_single_use,
            survey=survey,
            published_version=published_version,
            link=link,
        )
