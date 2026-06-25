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
from app.core.extensions import app_cache
from app.crypto import get_crypto_services
from app.crypto.services.linkage_key_service import LinkageKey
from app.domain.errors import (
    EnvelopeNotFoundError,
    SessionExpiredError,
    SessionInvalidError,
    SessionNotFoundError,
)
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_envelope_repo
from app.schema.orm.core.survey import SurveyVersion
from app.schema.orm.response.response_envelope import ResponseEnvelope

if TYPE_CHECKING:
    from app.schema.orm.core.submission_session import SubmissionSession

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
    linkage_key: LinkageKey


_FORBIDDEN_EDIT_STATUSES = frozenset({"abandoned"})


def _get_encryption_settings() -> EncryptionSettings:
    settings = current_settings()
    enc_cfg = settings.flowform.encryption
    if enc_cfg is None:
        raise SessionInvalidError("Encryption settings not configured")
    return enc_cfg


def load_current_session(
    db: Session,
    response_db: Session,
    raw_resume_token: str,
    *,
    allow_completed: bool = False,
) -> SessionContext:
    """Load and validate the current session from a browser resume token.

    Raises domain errors for every forbidden edit state:
    missing, expired, abandoned, and completed (unless allow_completed).
    """
    enc = _get_encryption_settings()

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

    wctx = app_cache.sessions.write_context.get(token_hash)
    if wctx is not None:
        envelope = response_db.get(ResponseEnvelope, wctx.envelope_id)
        if envelope is not None:
            return SessionContext(
                session=session,
                survey_version=survey_version,
                session_locator=wctx.session_locator,
                envelope=envelope,
                encryption_settings=enc,
                linkage_key=wctx.linkage_key,
            )
        app_cache.sessions.write_context.evict(token_hash)

    loc_svc = get_crypto_services().locator_service
    session_locator, linkage_key = loc_svc.for_existing_session(session.id, session.linkage_key_version, db)

    envelope = response_envelope_repo.get_by_locator(response_db, session_locator)
    if envelope is None:
        raise EnvelopeNotFoundError()

    return SessionContext(
        session=session,
        survey_version=survey_version,
        session_locator=session_locator,
        envelope=envelope,
        encryption_settings=enc,
        linkage_key=linkage_key,
    )
