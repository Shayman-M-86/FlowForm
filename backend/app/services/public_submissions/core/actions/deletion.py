"""Response-first deletion service.

Deletes encrypted response material before core metadata, per doc 06.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings
from app.crypto.services import LocatorService
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import EnvelopeNotFoundError
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_envelope_repo
from app.schema.orm.core.submission_session import SubmissionSession
from app.services.public_submissions.core.shared.session_crypto import resolve_session_crypto_services
from app.services.results import DeletionResult


def delete_session_responses(
    db: Session,
    response_db: Session,
    *,
    session: SubmissionSession,
    encryption_settings: EncryptionSettings | None = None,
    locator_service: LocatorService | None = None,
) -> DeletionResult:
    """Delete response data first, then core session.

    Response-first ordering is mandatory per doc 06.
    """
    loc_svc = resolve_session_crypto_services(
        encryption_settings, locator_service=locator_service,
    ).locator_service
    session_locator = loc_svc.for_existing_session(
        str(session.id), session.linkage_key_version, db,
    )

    # Step 1: Delete response DB records (cascade deletes answers + revisions)
    deleted = response_envelope_repo.delete_by_locator(response_db, session_locator)
    if not deleted:
        raise EnvelopeNotFoundError()

    commit_with_err_handle(response_db, contexts=[])

    # Step 2: Delete core session.
    ssr.delete_session(db, submission_session=session)
    commit_with_err_handle(db, contexts=[session])

    return DeletionResult(
        session_id=str(session.id),
        response_deleted=True,
        core_deleted=True,
    )
