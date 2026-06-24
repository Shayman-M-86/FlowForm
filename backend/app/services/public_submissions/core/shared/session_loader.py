"""Shared current-session loader for answer save, question-viewed, and completion.

Reads the browser resume token, loads the core session and frozen survey
version, rejects forbidden edit states, derives the session locator, and
loads the response envelope — returning a safe service context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings, current_settings
from app.crypto.services import LocatorService
from app.domain.errors import (
    EnvelopeNotFoundError,
    SessionExpiredError,
    SessionInvalidError,
    SessionNotFoundError,
)
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_envelope_repo
from app.schema.orm.core.survey import SurveyVersion
from app.services.public_submissions.core.shared.crypto_provider import get_crypto_services

if TYPE_CHECKING:
    from app.schema.orm.core.submission_session import SubmissionSession
    from app.schema.orm.response.response_envelope import ResponseEnvelope

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SessionContext:
    """Service-internal context returned by the session loader.

    Available to internal callers (answer save, completion, admin decrypt)
    for crypto operations. Fields like session_locator and envelope must
    never appear in respondent-facing API responses.
    """

    session: SubmissionSession
    survey_version: SurveyVersion
    session_locator: bytes
    envelope: ResponseEnvelope
    encryption_settings: EncryptionSettings


_FORBIDDEN_EDIT_STATUSES = frozenset({"abandoned"})


def _get_encryption_settings(enc: EncryptionSettings | None) -> EncryptionSettings:
    if enc is not None:
        return enc
    settings = current_settings()
    enc_cfg = settings.flowform.encryption
    if enc_cfg is None:
        raise SessionInvalidError("Encryption settings not configured")
    return enc_cfg


def _get_locator_service(
    locator_service: LocatorService | None,
    enc: EncryptionSettings | None,
) -> LocatorService:
    if locator_service is not None:
        return locator_service
    return get_crypto_services(enc).locator_service


def load_current_session(
    db: Session,
    response_db: Session,
    raw_resume_token: str,
    *,
    allow_completed: bool = False,
    encryption_settings: EncryptionSettings | None = None,
    locator_service: LocatorService | None = None,
) -> SessionContext:
    """Load and validate the current session from a browser resume token.

    Raises domain errors for every forbidden edit state:
    missing, expired, abandoned, and completed (unless allow_completed).
    """
    enc = _get_encryption_settings(encryption_settings)

    token_hash = ssr.hash_browser_session_token(raw_resume_token)
    session = ssr.get_by_token_hash(db, token_hash)
    if session is None:
        raise SessionNotFoundError()

    now = datetime.now(UTC)
    expires_at = session.expires_at.replace(tzinfo=UTC) if session.expires_at.tzinfo is None else session.expires_at
    if now > expires_at:
        raise SessionExpiredError()

    if session.session_status in _FORBIDDEN_EDIT_STATUSES:
        raise SessionInvalidError(f"Session is {session.session_status}.")

    if session.session_status == "completed" and not allow_completed:
        raise SessionInvalidError("Session is already completed.")

    survey_version = db.scalar(select(SurveyVersion).where(SurveyVersion.id == session.survey_version_id))
    if survey_version is None:
        raise SessionInvalidError("Frozen survey version not found.")

    loc_svc = _get_locator_service(locator_service, encryption_settings)
    session_locator = loc_svc.for_existing_session(session.id, session.linkage_key_version, db)

    envelope = response_envelope_repo.get_by_locator(response_db, session_locator)
    if envelope is None:
        raise EnvelopeNotFoundError()

    return SessionContext(
        session=session,
        survey_version=survey_version,
        session_locator=session_locator,
        envelope=envelope,
        encryption_settings=enc,
    )
