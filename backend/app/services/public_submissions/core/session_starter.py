"""Orchestrate access resolution, subject resolution, and submission session creation.

Entry point for all session-start flows (public slug, general link, private link,
authenticated link). Resolves the survey and access grant, determines the final
ProjectSubject, applies merge and identity writes, issues or rotates the recognition
token, creates the session row, creates the response envelope, and consumes
single-use links — committing both databases before returning the resume token.
"""
from __future__ import annotations

import logging
import os

from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings, current_settings
from app.crypto import DekCache, derive_session_locator, get_linkage_secret, wrap_dek
from app.crypto.kms import KmsError
from app.crypto.secrets import LinkageSecretError
from app.db.error_handling import commit_with_err_handle
from app.domain import survey_rules
from app.repositories import public_link_repo as plr
from app.repositories.core import project_subject_identities as sub_id
from app.repositories.core import project_subjects as subjects
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_envelope_repo
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.api.responses.submission_sessions import PublicSubmissionSessionResponses
from app.schema.orm.core.user import User
from app.services.public_submissions.core.access_resolver import AccessResolver
from app.services.public_submissions.core.subject_resolver import SubjectResolver
from app.services.public_submissions.core.subject_token import SubjectTokenService

logger = logging.getLogger(__name__)

_DEK_LENGTH = 32
_CRYPTO_VERSION = 1
_KMS_CONTEXT_VERSION = 1


class SessionStartError(Exception):
    """Raised when session start fails during envelope creation."""


class SessionStarter:
    """Orchestrate a respondent session start end-to-end.

    Sequence:
      1. AccessResolver  → SubmissionAccessGrant
      2. SubjectTokenService.lookup
      3. SubjectResolver → SubjectResolutionResult
      4. Apply merge writes, identity writes, token mechanics
      5. Create core session row, consume single-use link (flush, no commit)
      6. Derive session locator, generate DEK, wrap with KMS
      7. Create response envelope (flush in response DB)
      8. Commit response DB, then commit core DB
      9. Cache plaintext DEK
      10. Return session response + raw tokens
    """

    def __init__(
        self,
        *,
        access_resolver: AccessResolver | None = None,
        subject_resolver: SubjectResolver | None = None,
        token_service: SubjectTokenService | None = None,
        dek_cache: DekCache | None = None,
        encryption_settings: EncryptionSettings | None = None,
    ) -> None:
        self._token_service = token_service or SubjectTokenService()
        self._access_resolver = access_resolver or AccessResolver()
        self._subject_resolver = subject_resolver or SubjectResolver(token_service=self._token_service)
        self._dek_cache = dek_cache
        self._encryption_settings = encryption_settings

    def _get_encryption_settings(self) -> EncryptionSettings:
        if self._encryption_settings is not None:
            return self._encryption_settings
        settings = current_settings()
        enc = settings.flowform.encryption
        if enc is None:
            raise SessionStartError("Encryption settings not configured")
        return enc

    def start(
        self,
        db: Session,
        response_db: Session,
        *,
        payload: StartSubmissionSessionRequest,
        actor: User | None,
        recognition_token: str | None = None,
    ) -> tuple[PublicSubmissionSessionResponses, str, str | None]:
        """Run the full session-start sequence.

        Returns (session_response, raw_browser_session_token, raw_recognition_token).
        raw_recognition_token is None when token_action is "none".

        The browser resume token is not returned until both the core session
        and the response envelope have committed.
        """
        access = self._access_resolver.resolve(db, payload=payload, actor=actor)
        response_store_id = survey_rules.ensure_has_response_store(survey=access.survey)

        lookup = self._token_service.lookup(
            db, project_id=access.project_id, raw_token=recognition_token
        ) if recognition_token else None

        token_subject_id = lookup.token_subject_id if (lookup and lookup.token_valid) else None
        canonical_token_subject_id = lookup.canonical_token_subject_id if (lookup and lookup.token_valid) else None

        resolution = self._subject_resolver.resolve(
            db,
            project_id=access.project_id,
            access_method=access.access_method,
            assigned_subject_id=access.assigned_subject_id,
            token_subject_id=token_subject_id,
            canonical_token_subject_id=canonical_token_subject_id,
            actor_user_id=actor.id if actor is not None else None,
        )

        final_subject_id = resolution.final_subject_id

        if resolution.merge_subject_id is not None and resolution.merge_into_subject_id is not None:
            weaker = subjects.get_subject(
                db, project_id=access.project_id, subject_id=resolution.merge_subject_id
            )
            stronger = subjects.get_subject(
                db, project_id=access.project_id, subject_id=resolution.merge_into_subject_id
            )
            if weaker is not None and stronger is not None:
                subjects.set_canonical_subject(db, subject=weaker, canonical=stronger)

        if actor is not None and resolution.needs_identity_write:
            sub_id.create_user_identity(
                db,
                project_id=access.project_id,
                project_subject_id=final_subject_id,
                user=actor,
            )

        raw_recognition_token: str | None = self._token_service.apply_token_action(
            db,
            project_id=access.project_id,
            final_subject_id=final_subject_id,
            token_action=resolution.token_action,
            existing_raw_token=recognition_token,
        )

        raw_browser_session_token = ssr.generate_browser_session_token()
        session = ssr.create_session(
            db,
            project_id=access.project_id,
            survey_id=access.survey_id,
            survey_version_id=access.survey_version_id,
            response_store_id=response_store_id,
            link_id=access.link_id,
            project_subject_id=final_subject_id,
            raw_browser_session_token=raw_browser_session_token,
        )

        if access.link is not None and access.is_single_use:
            plr.mark_used(db, link=access.link)

        # --- Response envelope creation ---
        # Core rows are flushed but NOT committed yet. If envelope creation
        # fails, core rollback undoes the session, single-use link consumption,
        # and recognition-token side effects.
        try:
            session_locator, plaintext_dek = self._create_response_envelope(
                db, response_db, session=session
            )
        except SessionStartError:
            raise
        except Exception:
            logger.error("session_start.envelope_creation_failed")
            db.rollback()
            raise SessionStartError("Failed to create response envelope")

        if access.link is not None and access.is_single_use:
            commit_with_err_handle(db, contexts=[session, access.link])
        else:
            commit_with_err_handle(db, contexts=[session])

        # Both DBs committed — safe to return tokens.
        survey_schema = (
            access.published_version.compiled_schema
            if access.access_method == "public_slug"
            else None
        )

        if self._dek_cache is not None:
            self._dek_cache.put(session_locator, plaintext_dek)

        response = PublicSubmissionSessionResponses(
            status=session.session_status,
            started_at=session.started_at,
            expires_at=session.expires_at,
            survey_version_id=access.survey_version_id,
            survey_schema=survey_schema,
        )
        return response, raw_browser_session_token, raw_recognition_token

    def _create_response_envelope(
        self,
        db: Session,
        response_db: Session,
        *,
        session: object,
    ) -> tuple[bytes, bytes]:
        """Derive locator, generate and wrap DEK, create envelope, commit response DB.

        Returns (session_locator, plaintext_dek).
        On failure: rolls back core so no side effects leak.
        """
        from app.schema.orm.core.submission_session import SubmissionSession

        assert isinstance(session, SubmissionSession)

        enc = self._get_encryption_settings()
        core_session_id = str(session.id)
        linkage_key_version = session.linkage_key_version

        try:
            linkage_secret = get_linkage_secret(
                enc.linkage_secret_arn,
                region=enc.aws_region,
                access_key_id=enc.aws_access_key_id,
                secret_access_key=enc.aws_secret_access_key,
            )
            session_locator = derive_session_locator(core_session_id, linkage_secret)

            plaintext_dek = os.urandom(_DEK_LENGTH)
            kms_context = {
                "session_locator": session_locator.hex(),
                "kms_context_version": str(_KMS_CONTEXT_VERSION),
            }
            wrapped_dek = wrap_dek(
                plaintext_dek,
                enc.kms_key_arn,
                kms_context,
                region=enc.aws_region,
                access_key_id=enc.aws_access_key_id,
                secret_access_key=enc.aws_secret_access_key,
            )

            response_envelope_repo.create(
                response_db,
                session_locator=session_locator,
                linkage_key_version=linkage_key_version,
                wrapped_dek=wrapped_dek,
                kms_key_arn=enc.kms_key_arn,
                kms_context_version=_KMS_CONTEXT_VERSION,
                crypto_version=_CRYPTO_VERSION,
            )

            commit_with_err_handle(response_db, contexts=[])

        except (KmsError, LinkageSecretError):
            logger.error("session_start.envelope_creation_failed")
            db.rollback()
            raise SessionStartError("Failed to create response envelope")
        except Exception:
            logger.error("session_start.envelope_creation_failed")
            db.rollback()
            raise SessionStartError("Failed to create response envelope")

        return session_locator, plaintext_dek
