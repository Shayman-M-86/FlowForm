"""Start public submission sessions.

Coordinates access resolution, subject resolution, core session creation,
response envelope creation, and final commit/cleanup.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings, current_settings
from app.crypto.errors import SurveyBranchKeyUnavailableError
from app.crypto.services import LocatorService, SessionDEKService, SurveyBranchKeyService
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import SessionStartError
from app.repositories import public_link_repo as plr
from app.repositories.core import project_subject_identities as sub_id
from app.repositories.core import project_subjects as subjects
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_envelope_repo
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.api.responses.submission_sessions import StartSubmissionSessionResponse
from app.schema.orm.core.user import User
from app.services.public_submissions.core.resolution.access_resolver import AccessResolver
from app.services.public_submissions.core.resolution.subject_resolver import SubjectResolver
from app.services.public_submissions.core.resolution.subject_token import SubjectTokenService
from app.services.public_submissions.core.shared.crypto_provider import CryptoServices
from app.services.public_submissions.core.shared.session_crypto import (
    build_session_dek_wrap_aad,
    load_survey_encryption_key,
    resolve_session_crypto_services,
)
from app.services.results import SubjectResolutionResult, SubmissionAccessGrant

if TYPE_CHECKING:
    from app.schema.orm.core.submission_session import SubmissionSession


logger = logging.getLogger(__name__)

_CRYPTO_VERSION = 1


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
        subject_resolver: SubjectResolver | None = None,
        token_service: SubjectTokenService | None = None,
        locator_service: LocatorService | None = None,
        dek_service: SessionDEKService | None = None,
        survey_branch_key_service: SurveyBranchKeyService | None = None,
        encryption_settings: EncryptionSettings | None = None,
    ) -> None:
        self._token_service = token_service or SubjectTokenService()
        self._access_resolver = access_resolver or AccessResolver()
        self._subject_resolver = subject_resolver or SubjectResolver(
            token_service=self._token_service,
        )

        self._encryption_settings = encryption_settings
        self._locator_service_override = locator_service
        self._dek_service_override = dek_service
        self._survey_branch_key_service_override = survey_branch_key_service

        self._crypto: CryptoServices | None = None

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

        resolution = self._resolve_subject(
            db,
            access=access,
            actor=actor,
            recognition_token=recognition_token,
        )

        self._apply_subject_writes(
            db,
            access=access,
            actor=actor,
            resolution=resolution,
        )

        raw_recognition_token = self._apply_token_action(
            db,
            access=access,
            resolution=resolution,
            existing_raw_token=recognition_token,
        )

        linkage_key_version = self._current_linkage_key_version(db)

        session, raw_browser_session_token = self._create_core_session(
            db,
            access=access,
            project_subject_id=resolution.final_subject_id,
            linkage_key_version=linkage_key_version,
        )

        self._consume_single_use_link_if_needed(db, access)

        session_locator = self._create_response_envelope(
            db,
            response_db,
            session=session,
        )

        self._commit_core_or_cleanup_envelope(
            db,
            response_db,
            access=access,
            session=session,
            session_locator=session_locator,
        )

        response = self._build_response(access, session)
        return response, raw_browser_session_token, raw_recognition_token

    def _resolve_subject(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        actor: User | None,
        recognition_token: str | None,
    ) -> SubjectResolutionResult:
        token_subject_id, canonical_token_subject_id = self._lookup_token_subject_ids(
            db,
            project_id=access.project_id,
            raw_token=recognition_token,
        )

        return self._subject_resolver.resolve(
            db,
            project_id=access.project_id,
            access_method=access.access_method,
            assigned_subject_id=access.assigned_subject_id,
            token_subject_id=token_subject_id,
            canonical_token_subject_id=canonical_token_subject_id,
            actor_user_id=actor.id if actor is not None else None,
        )

    def _lookup_token_subject_ids(
        self,
        db: Session,
        *,
        project_id: int,
        raw_token: str | None,
    ) -> tuple[UUID | None, UUID | None]:
        if not raw_token:
            return None, None

        lookup = self._token_service.lookup(
            db,
            project_id=project_id,
            raw_token=raw_token,
        )

        if not lookup.token_valid:
            return None, None

        return lookup.token_subject_id, lookup.canonical_token_subject_id

    def _apply_subject_writes(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        actor: User | None,
        resolution: SubjectResolutionResult,
    ) -> None:
        self._merge_subject_if_needed(db, access=access, resolution=resolution)
        self._write_actor_identity_if_needed(
            db,
            access=access,
            actor=actor,
            resolution=resolution,
        )

    def _merge_subject_if_needed(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        resolution: SubjectResolutionResult,
    ) -> None:
        if resolution.merge_subject_id is None:
            return

        if resolution.merge_into_subject_id is None:
            return

        weaker = subjects.get_subject(
            db,
            project_id=access.project_id,
            subject_id=resolution.merge_subject_id,
        )

        stronger = subjects.get_subject(
            db,
            project_id=access.project_id,
            subject_id=resolution.merge_into_subject_id,
        )

        if weaker is None or stronger is None:
            return

        subjects.set_canonical_subject(db, subject=weaker, canonical=stronger)

    def _write_actor_identity_if_needed(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        actor: User | None,
        resolution: SubjectResolutionResult,
    ) -> None:
        if actor is None:
            return

        if not resolution.needs_identity_write:
            return

        sub_id.create_user_identity(
            db,
            project_id=access.project_id,
            project_subject_id=resolution.final_subject_id,
            user=actor,
        )

    def _apply_token_action(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        resolution: SubjectResolutionResult,
        existing_raw_token: str | None,
    ) -> str | None:
        return self._token_service.apply_token_action(
            db,
            project_id=access.project_id,
            final_subject_id=resolution.final_subject_id,
            token_action=resolution.token_action,
            existing_raw_token=existing_raw_token,
        )

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
        if access.link is None or not access.is_single_use:
            return

        plr.mark_used(db, link=access.link)

    def _create_response_envelope(
        self,
        db: Session,
        response_db: Session,
        *,
        session: SubmissionSession,
    ) -> bytes:
        """Create and commit the response envelope.

        Core rows are flushed, but not committed yet. If response envelope
        creation fails, the core transaction is rolled back.
        """
        crypto = self._ensure_crypto()

        try:
            branch_key_service = crypto.survey_branch_key_service
            if branch_key_service is None:
                raise SurveyBranchKeyUnavailableError()

            loc = crypto.locator_service.for_new_session(session.id, db)
            survey_key = load_survey_encryption_key(db, session=session)
            plaintext_branch_key = branch_key_service.get_plaintext_key(survey_key)
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

            response_envelope_repo.create(
                response_db,
                session_locator=loc.session_locator,
                linkage_key_version=loc.linkage_key_version,
                wrapped_session_dek=new_dek.wrapped_session_dek,
                crypto_version=_CRYPTO_VERSION,
            )

            commit_with_err_handle(response_db, contexts=[])

        except Exception as err:
            logger.error("session_start.envelope_creation_failed", exc_info=True)
            db.rollback()
            raise SessionStartError("Failed to create response envelope") from err

        return loc.session_locator

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

    def _current_linkage_key_version(self, db: Session) -> int:
        crypto = self._ensure_crypto()
        return crypto.locator_service.get_current_linkage_key_version(db)

    def _ensure_crypto(self) -> CryptoServices:
        """Lazily build crypto services on first use."""
        if self._crypto is not None:
            return self._crypto

        self._crypto = resolve_session_crypto_services(
            self._get_encryption_settings(),
            locator_service=self._locator_service_override,
            dek_service=self._dek_service_override,
            survey_branch_key_service=self._survey_branch_key_service_override,
        )
        return self._crypto

    def _get_encryption_settings(self) -> EncryptionSettings:
        if self._encryption_settings is not None:
            return self._encryption_settings

        enc = current_settings().flowform.encryption

        if enc is None:
            raise SessionStartError("Encryption settings not configured")

        self._encryption_settings = enc
        return enc

    @staticmethod
    def _build_response(
        access: SubmissionAccessGrant,
        session: SubmissionSession,
    ) -> StartSubmissionSessionResponse:
        return StartSubmissionSessionResponse(
            status=session.session_status,
            started_at=session.started_at,
            expires_at=session.expires_at,
            survey_version_id=access.survey_version_id,
        )
