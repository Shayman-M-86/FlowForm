from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain import survey_rules
from app.repositories import public_link_repo as plr
from app.repositories.core import submission_sessions as ssr
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.api.responses.submission_sessions import (
    PublicSubmissionSessionResponses,
    PublicSubmissionSessionSurveyResponses,
    PublicSubmissionSessionVersionResponses,
)
from app.schema.orm.core.user import User
from app.services.submissions.access_resolver import SurveyAccessResolver
from app.services.submissions.project_subject_resolver import ProjectSubjectResolver


class SessionStarter:
    """Create core submission sessions after access and subject resolution."""

    def __init__(
        self,
        *,
        access_resolver: SurveyAccessResolver | None = None,
        subject_resolver: ProjectSubjectResolver | None = None,
    ) -> None:
        self._access_resolver = access_resolver or SurveyAccessResolver()
        self._subject_resolver = subject_resolver or ProjectSubjectResolver()

    def start(
        self,
        db: Session,
        *,
        payload: StartSubmissionSessionRequest,
        actor: User | None,
        recognition_token: str | None = None,
    ) -> tuple[PublicSubmissionSessionResponses, str]:
        access = self._access_resolver.resolve(db, payload=payload, actor=actor)
        response_store_id = survey_rules.ensure_has_response_store(survey=access.survey)
        resolved_subject = self._subject_resolver.resolve(
            db,
            project_id=access.survey.project_id,
            link=access.link,
            actor=actor,
            recognition_token=recognition_token,
            create_anonymous_subject=False,
        )
        subject = resolved_subject.subject
        raw_browser_session_token = ssr.generate_browser_session_token()
        session = ssr.create_session(
            db,
            project_id=access.survey.project_id,
            survey_id=access.survey.id,
            survey_version_id=access.published_version.id,
            response_store_id=response_store_id,
            link_id=access.link.id if access.link is not None else None,
            project_subject_id=subject.id if subject is not None else None,
            raw_browser_session_token=raw_browser_session_token,
        )
        # Only single-use (assigned) links are consumed. Stamping used_at on an
        # unassigned reusable link violates ck_survey_links_used_at_requires_assignment.
        if access.link is not None and access.link.is_single_use:
            plr.mark_used(db, link=access.link)

        commit_with_err_handle(db, contexts=[session])
        response = PublicSubmissionSessionResponses(
            status=session.session_status,
            started_at=session.started_at,
            expires_at=session.expires_at,
            survey=PublicSubmissionSessionSurveyResponses(id=access.survey.id, title=access.survey.title),
            version=PublicSubmissionSessionVersionResponses(
                id=access.published_version.id,
                version_number=access.published_version.version_number,
                compiled_schema=access.published_version.compiled_schema or {},
            ),
            answers=[],
        )
        return response, raw_browser_session_token
