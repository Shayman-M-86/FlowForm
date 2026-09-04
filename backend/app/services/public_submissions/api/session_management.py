"""Respondent submission-session lifecycle: start, answer, event, complete.

API-facing entry point. Routes in api/v1/respondent/ call this service directly.
Start delegates to core/session_starter.py. Answer delegates to
core/answer_save.py. Complete delegates to core/completion.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.cache import get_app_cache
from app.crypto._internal.client_extension import get_crypto_clients
from app.domain.errors import SessionNotFoundError
from app.repositories import public_link_repo as plr
from app.repositories import surveys_repo as sr
from app.schema.api.content.common import FieldId
from app.schema.api.content.survey_document import SurveyDocumentAnswerValue
from app.schema.api.requests.submission_sessions import (
    StartSubmissionSessionRequest,
)
from app.schema.api.responses.submission_sessions import (
    ResumeSubmissionSessionResponse,
    StartSubmissionSessionResponse,
)
from app.schema.api.responses.surveys import SurveyResponses, SurveyVersionResponses
from app.schema.enums import SubmissionAnswerState
from app.schema.orm.core.survey import SurveyVersion
from app.schema.orm.core.user import User
from app.services.public_submissions.core.actions.answer_save import AnswerSaveService
from app.services.public_submissions.core.actions.completion import (
    CompletionResult,
    complete_session,
)
from app.services.public_submissions.core.actions.session_starter import SessionStarter
from app.services.public_submissions.core.resolution.access_resolver import AccessResolver
from app.services.public_submissions.core.resolution.session_subject_service import SessionSubjectService
from app.services.public_submissions.core.resolution.subject_resolver import SubjectResolver
from app.services.public_submissions.core.resolution.subject_token import SubjectTokenService
from app.services.public_submissions.core.session_loader import (
    load_current_session,
    load_current_session_record,
)
from app.services.results import AnswerSaveResult

if TYPE_CHECKING:
    from app.cache import AppCache
    from app.crypto._internal.client_extension import CryptoClients


class SessionManagementService:
    """Full respondent session lifecycle."""

    def __init__(
        self,
        *,
        session_starter: SessionStarter | None = None,
        answer_save_service: AnswerSaveService | None = None,
        access_resolver: AccessResolver | None = None,
        subject_service: SessionSubjectService | None = None,
        subject_resolver: SubjectResolver | None = None,
        token_service: SubjectTokenService | None = None,
        cache: AppCache | None = None,
        clients: CryptoClients | None = None,
    ) -> None:
        self._cache = cache
        self._clients = clients
        self._session_starter = session_starter
        self._access_resolver = access_resolver or AccessResolver()
        self._subject_service = subject_service or SessionSubjectService()
        self._subject_resolver = subject_resolver or SubjectResolver()
        self._token_service = token_service or SubjectTokenService()
        self._answer_save_service = answer_save_service or AnswerSaveService()

    def _cache_and_clients(self) -> tuple[AppCache, CryptoClients]:
        return self._cache or get_app_cache(), self._clients or get_crypto_clients()

    def _starter(self) -> SessionStarter:
        cache, clients = self._cache_and_clients()
        return self._session_starter or SessionStarter(
            access_resolver=self._access_resolver,
            subject_service=self._subject_service,
            subject_resolver=self._subject_resolver,
            token_service=self._token_service,
            cache=cache,
            clients=clients,
        )

    def start_session(
        self,
        db: Session,
        response_db: Session,
        *,
        payload: StartSubmissionSessionRequest,
        actor: User | None,
        recognition_token: str | None = None,
    ) -> tuple[StartSubmissionSessionResponse, str, str | None]:
        """Start a respondent submission session.

        Returns (session_response, raw_browser_session_token, raw_recognition_token).
        The route sets the browser-session and recognition cookies from the raw tokens.
        """
        return self._starter().start(db, response_db, payload=payload, actor=actor, recognition_token=recognition_token)

    def resume_session(
        self,
        db: Session,
        *,
        payload: StartSubmissionSessionRequest,
        raw_resume_token: str | None,
    ) -> ResumeSubmissionSessionResponse:
        """Return the pinned survey context for a matching browser session.

        The entry descriptor prevents a cookie from one survey being resumed
        on another survey's URL. Link state is not re-resolved: after a
        successful start, the browser resume token is the continuity
        credential and a single-use link may already be consumed.
        """
        if raw_resume_token is None:
            raise SessionNotFoundError()

        session = load_current_session_record(db, raw_resume_token)
        access = payload.access
        if access.type == "link_token":
            link = plr.resolve_token(db, access.token)
            if link is None or session.link_id != link.id:
                raise SessionNotFoundError()
        else:
            survey_for_slug = sr.get_survey(
                db,
                project_id=session.project_id,
                survey_id=session.survey_id,
            )
            if (
                session.link_id is not None
                or survey_for_slug is None
                or survey_for_slug.public_slug != access.public_slug
            ):
                raise SessionNotFoundError()

        survey = sr.get_survey(
            db,
            project_id=session.project_id,
            survey_id=session.survey_id,
        )
        version = db.get(SurveyVersion, session.survey_version_id)
        if survey is None or version is None or version.survey_id != survey.id:
            raise SessionNotFoundError()

        return ResumeSubmissionSessionResponse(
            status=session.session_status,
            survey=SurveyResponses.model_validate(survey),
            published_version=SurveyVersionResponses.model_validate(version),
        )

    def complete_session(
        self,
        db: Session,
        response_db: Session,
        *,
        raw_resume_token: str | None,
    ) -> CompletionResult:
        """Complete a respondent session.

        Loads the session from the browser resume token, then delegates to
        the completion action for the state transition.
        """
        if raw_resume_token is None:
            raise SessionNotFoundError()

        cache, clients = self._cache_and_clients()
        ctx = load_current_session(
            db,
            response_db,
            raw_resume_token,
            allow_completed=True,
            cache=cache,
            clients=clients,
        )
        return complete_session(db, ctx=ctx)

    def save_answer(
        self,
        db: Session,
        response_db: Session,
        *,
        raw_resume_token: str | None,
        field_id: FieldId,
        answer_state: SubmissionAnswerState,
        answer_value: SurveyDocumentAnswerValue | None,
        client_mutation_id: UUID,
    ) -> AnswerSaveResult:
        """Save a respondent answer. Returns the save result."""
        if raw_resume_token is None:
            raise SessionNotFoundError()
        cache, clients = self._cache_and_clients()
        ctx = load_current_session(
            db,
            response_db,
            raw_resume_token,
            cache=cache,
            clients=clients,
        )
        return self._answer_save_service.save_answer(
            db,
            response_db,
            ctx=ctx,
            field_id=field_id,
            answer_state=answer_state,
            answer_value=answer_value,
            client_mutation_id=client_mutation_id,
        )

    def record_field_viewed(
        self,
        db: Session,
        response_db: Session,
        *,
        raw_resume_token: str | None,
        field_id: FieldId,
    ) -> None:
        """Record a field-viewed analytics event."""
        if raw_resume_token is None:
            raise SessionNotFoundError()
        cache, clients = self._cache_and_clients()
        ctx = load_current_session(
            db,
            response_db,
            raw_resume_token,
            cache=cache,
            clients=clients,
        )
        self._answer_save_service.record_field_viewed(
            db,
            ctx=ctx,
            field_id=field_id,
        )
