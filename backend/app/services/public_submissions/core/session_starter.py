"""Orchestrate access resolution, subject resolution, and submission session creation.

Docs: docs/Policies and Services/service-structure.md — How the layers relate
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain import survey_rules
from app.repositories import public_link_repo as plr
from app.repositories.core import submission_sessions as ssr
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.api.responses.submission_sessions import PublicSubmissionSessionResponses
from app.schema.orm.core.user import User
from app.services.public_submissions.core.access_resolver import AccessResolver
from app.services.public_submissions.core.subject_resolver import SubjectResolver
from app.services.public_submissions.core.subject_token import SubjectTokenService


class SessionStarter:
    """Orchestrate a respondent session start end-to-end.

    Sequence:
      1. AccessResolver  → SubmissionAccessGrant   (which survey, which link, visibility check)
      2. SubjectResolver → ResolvedProjectSubject  (who is this respondent)
      3. SubjectTokenService.issue                 (recognition token for the resolved subject)
      4. DB write: create submission session row, consume single-use link
      5. Return session response + raw recognition token

    No access or subject logic lives here — this class only orchestrates.
    """

    def __init__(
        self,
        *,
        access_resolver: AccessResolver | None = None,
        subject_resolver: SubjectResolver | None = None,
        token_service: SubjectTokenService | None = None,
    ) -> None:
        self._token_service = token_service or SubjectTokenService()
        self._access_resolver = access_resolver or AccessResolver()
        self._subject_resolver = subject_resolver or SubjectResolver(token_service=self._token_service)

    def start(
        self,
        db: Session,
        *,
        payload: StartSubmissionSessionRequest,
        actor: User | None,
        recognition_token: str | None = None,
    ) -> tuple[PublicSubmissionSessionResponses, str, str | None]:
        """Run the full session-start sequence.

        Returns (session_response, raw_browser_session_token, raw_recognition_token).
        raw_recognition_token is None when the resolved subject is None (no tracking).
        """
        access = self._access_resolver.resolve(db, payload=payload, actor=actor)
        response_store_id = survey_rules.ensure_has_response_store(survey=access.survey)

        resolved_subject = self._subject_resolver.resolve(
            db,
            project_id=access.survey.project_id,
            link=access.link,
            actor=actor,
            recognition_token=recognition_token,
        )
        subject = resolved_subject.subject

        raw_recognition_token: str | None = None
        if subject is not None:
            raw_recognition_token = self._token_service.issue(
                db, project_id=access.survey.project_id, subject=subject
            )

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

        if access.link is not None and access.link.is_single_use:
            plr.mark_used(db, link=access.link)

        commit_with_err_handle(db, contexts=[session])

        response = PublicSubmissionSessionResponses(
            status=session.session_status,
            started_at=session.started_at,
            expires_at=session.expires_at,
            survey_version_id=access.published_version.id,
        )
        return response, raw_browser_session_token, raw_recognition_token
