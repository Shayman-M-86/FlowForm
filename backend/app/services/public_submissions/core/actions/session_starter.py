"""Start public submission sessions.

Coordinates access resolution, subject resolution, core session creation,
response envelope creation, and final commit/cleanup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.cache.sessions import SessionWriteContext
from app.core.extensions import app_cache
from app.crypto import get_crypto_services
from app.crypto._internal.errors import SurveyBranchKeyUnavailableError
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import SessionStartError
from app.logging.request_timing import request_timing
from app.repositories import public_link_repo as plr
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_envelope_repo
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.api.responses.submission_sessions import StartSubmissionSessionResponse
from app.schema.orm.core.user import User
from app.services.public_submissions.core.resolution.access_resolver import AccessResolver
from app.services.public_submissions.core.resolution.session_subject_service import (
    SessionSubjectService,
)
from app.services.public_submissions.core.resolution.subject_resolver import SubjectResolver
from app.services.public_submissions.core.resolution.subject_token import SubjectTokenService
from app.services.public_submissions.core.shared.session_crypto import (
    build_session_dek_wrap_aad,
    load_survey_encryption_key,
)
from app.services.results import SubmissionAccessGrant

if TYPE_CHECKING:
    from app.crypto.services.linkage_key_service import LinkageKey
    from app.schema.orm.core.submission_session import SubmissionSession


logger = logging.getLogger(__name__)

_CRYPTO_VERSION = 1


@dataclass(frozen=True, slots=True)
class _EnvelopeResult:
    session_locator: bytes
    plaintext_session_dek: bytes
    envelope_id: UUID
    linkage_key_version: int


class SessionStarter:
    """Orchestrate a respondent session start end-to-end.

    Flow:
      1. Resolve access.
      2. Resolve the subject.
      3. Apply subject writes.
      4. Apply token action.
      5. Create the core session.
      6. Create the response envelope.
      7. Commit core, or clean up the envelope if core commit fails.
      8. Return the session response and raw tokens.
    """

    def __init__(
        self,
        *,
        access_resolver: AccessResolver | None = None,
        subject_service: SessionSubjectService | None = None,
        subject_resolver: SubjectResolver | None = None,
        token_service: SubjectTokenService | None = None,
    ) -> None:
        token_service = token_service or SubjectTokenService()
        self._access_resolver = access_resolver or AccessResolver()
        self._subject_service = subject_service or SessionSubjectService(
            subject_resolver=subject_resolver,
            token_service=token_service,
        )

    def start(
        self,
        db: Session,
        response_db: Session,
        *,
        payload: StartSubmissionSessionRequest,
        actor: User | None,
        recognition_token: str | None = None,
    ) -> tuple[StartSubmissionSessionResponse, str, str | None]:
        """Start a submission session.

        Returns:
            session_response
            raw_browser_session_token
            raw_recognition_token, or None when token_action is "none"
        """
        access = self._access_resolver.resolve(db, payload=payload, actor=actor)
        request_timing.log("session_start.access_resolved")

        subject = self._subject_service.resolve_for_session_start(
            db,
            access=access,
            actor=actor,
            recognition_token=recognition_token,
        )

        linkage_key = self._current_linkage_key(db)
        request_timing.log("session_start.linkage_key_loaded")

        session, raw_browser_session_token = self._create_core_session(
            db,
            access=access,
            project_subject_id=subject.final_subject_id,
            linkage_key_version=linkage_key.version,
        )
        request_timing.log("session_start.core_session_created")

        self._consume_single_use_link_if_needed(db, access)
        request_timing.log("session_start.link_consumed_if_needed")

        envelope_result = self._create_response_envelope(
            db,
            response_db,
            session=session,
            linkage_key=linkage_key,
        )
        request_timing.log("session_start.response_envelope_created")

        self._commit_core_or_cleanup_envelope(
            db,
            response_db,
            access=access,
            session=session,
            session_locator=envelope_result.session_locator,
        )
        request_timing.log("session_start.core_committed")

        app_cache.sessions.write_context.put(
            session.browser_session_token_hash,
            SessionWriteContext(
                session_id=session.id,
                project_id=session.project_id,
                survey_id=session.survey_id,
                survey_version_id=session.survey_version_id,
                session_locator=envelope_result.session_locator,
                envelope_id=envelope_result.envelope_id,
                plaintext_session_dek=envelope_result.plaintext_session_dek,
                crypto_version=_CRYPTO_VERSION,
                expires_at=session.expires_at,
                linkage_key=linkage_key,
            ),
        )

        response = self._build_response(
            access,
            session,
            subject_code=subject.subject_code,
        )
        return response, raw_browser_session_token, subject.raw_recognition_token

    def _create_core_session(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        project_subject_id: UUID | None,
        linkage_key_version: int,
    ) -> tuple[SubmissionSession, str]:
        raw_browser_session_token = ssr.generate_browser_session_token()

        session = ssr.create_session(
            db,
            project_id=access.project_id,
            survey_id=access.survey_id,
            survey_version_id=access.survey_version_id,
            response_store_id=access.response_store_id,
            link_id=access.link_id,
            project_subject_id=project_subject_id,
            raw_browser_session_token=raw_browser_session_token,
            linkage_key_version=linkage_key_version,
        )

        return session, raw_browser_session_token

    def _consume_single_use_link_if_needed(
        self,
        db: Session,
        access: SubmissionAccessGrant,
    ) -> None:
        if not access.is_single_use:
            return

        if access.link_id is None:
            return

        plr.mark_used(db, link=access.link)  # type: ignore

    def _create_response_envelope(
        self,
        db: Session,
        response_db: Session,
        *,
        session: SubmissionSession,
        linkage_key: LinkageKey,
    ) -> _EnvelopeResult:
        """Create and commit the response envelope.

        Core rows are flushed, but not committed yet. If response envelope
        creation fails, the core transaction is rolled back.
        """
        crypto = get_crypto_services()

        try:
            branch_key_service = crypto.survey_branch_key_service
            if branch_key_service is None:
                raise SurveyBranchKeyUnavailableError()

            survey_key = load_survey_encryption_key(db, session=session)
            request_timing.log("session_start.envelope.survey_key_loaded")

            branch_key_resolver = branch_key_service.prefetch_plaintext_key(survey_key)

            loc = crypto.locator_service.for_new_session(
                session.id,
                db,
                linkage_key=linkage_key,
            )
            request_timing.log("session_start.envelope.locator_derived")

            plaintext_branch_key = branch_key_resolver()
            request_timing.log("session_start.envelope.branch_key_ready")
            wrap_aad = build_session_dek_wrap_aad(
                crypto_version=_CRYPTO_VERSION,
                project_id=session.project_id,
                survey_id=session.survey_id,
                session_id=session.id,
                session_locator=loc.session_locator,
            )

            new_dek = crypto.dek_service.create_for_session(
                session.id,
                plaintext_branch_key,
                session.expires_at,
                wrap_aad=wrap_aad,
            )
            request_timing.log("session_start.envelope.session_dek_wrapped")

            envelope = response_envelope_repo.create(
                response_db,
                session_locator=loc.session_locator,
                linkage_key_version=loc.linkage_key_version,
                wrapped_session_dek=new_dek.wrapped_session_dek,
                crypto_version=_CRYPTO_VERSION,
            )

            commit_with_err_handle(response_db, contexts=[])
            request_timing.log("session_start.envelope.response_committed")

        except Exception as err:
            logger.error("session_start.envelope_creation_failed", exc_info=True)
            db.rollback()
            raise SessionStartError("Failed to create response envelope") from err

        return _EnvelopeResult(
            session_locator=loc.session_locator,
            plaintext_session_dek=new_dek.plaintext_dek,
            envelope_id=envelope.id,
            linkage_key_version=loc.linkage_key_version,
        )

    def _commit_core_or_cleanup_envelope(
        self,
        db: Session,
        response_db: Session,
        *,
        access: SubmissionAccessGrant,
        session: SubmissionSession,
        session_locator: bytes,
    ) -> None:
        try:
            if access.link is not None and access.is_single_use:
                commit_with_err_handle(db, contexts=[session, access.link])
            else:
                commit_with_err_handle(db, contexts=[session])

        except Exception as err:
            self._compensate_orphan_envelope(response_db, session_locator)
            raise SessionStartError(
                "Core commit failed after response envelope creation",
            ) from err

    def _compensate_orphan_envelope(
        self,
        response_db: Session,
        session_locator: bytes,
    ) -> None:
        """Best-effort cleanup after response commit succeeds but core commit fails."""
        try:
            response_envelope_repo.delete_by_locator(response_db, session_locator)
            response_db.commit()

        except Exception:
            response_db.rollback()
            logger.critical(
                "session_start.orphan_envelope_cleanup_failed",
                exc_info=True,
            )

    def _current_linkage_key(self, db: Session) -> LinkageKey:
        return get_crypto_services().locator_service.get_current_linkage_key(db)

    @staticmethod
    def _build_response(
        access: SubmissionAccessGrant,
        session: SubmissionSession,
        *,
        subject_code: str,
    ) -> StartSubmissionSessionResponse:
        return StartSubmissionSessionResponse(
            status=session.session_status,
            started_at=session.started_at,
            expires_at=session.expires_at,
            survey_version_id=access.survey_version_id,
            subject_code=subject_code,
        )
