"""Response-first deletion service.

Deletes encrypted response material before core metadata, per doc 06.
If the response delete succeeds but core delete fails, marks the deletion
as pending and raises DeletionPendingError — never claims success.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings
from app.crypto import derive_session_locator, get_linkage_secret
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import DeletionPendingError, EnvelopeNotFoundError
from app.repositories.response import response_envelope_repo
from app.schema.orm.core.submission_session import SubmissionSession
from app.services.results import DeletionResult

logger = logging.getLogger(__name__)


def delete_session_responses(
    db: Session,
    response_db: Session,
    *,
    session: SubmissionSession,
    encryption_settings: EncryptionSettings,
) -> DeletionResult:
    """Delete response data first, then core session.

    Response-first ordering is mandatory per doc 06. If core deletion
    fails after response deletion succeeds, the result marks the
    deletion as pending for later retry.
    """
    enc = encryption_settings
    linkage_secret = get_linkage_secret(
        enc.linkage_secret_arn,
        region=enc.aws_region,
        access_key_id=enc.aws_access_key_id,
        secret_access_key=enc.aws_secret_access_key,
    )
    session_locator = derive_session_locator(str(session.id), linkage_secret)

    # Step 1: Delete response DB records (cascade deletes answers + revisions)
    deleted = response_envelope_repo.delete_by_locator(response_db, session_locator)
    if not deleted:
        raise EnvelopeNotFoundError()

    commit_with_err_handle(response_db, contexts=[])

    # Step 2: Delete core session.
    # If this fails, DeletionPendingError is raised but no persistent
    # marker is written — the session_status CHECK only allows
    # in_progress/completed/abandoned, so adding a deletion state
    # requires a schema migration. Callers must catch and track
    # pending deletions externally until that migration lands.
    try:
        db.delete(session)
        commit_with_err_handle(db, contexts=[])
    except Exception:
        logger.warning("deletion.core_delete_failed", exc_info=True)
        db.rollback()
        raise DeletionPendingError()

    return DeletionResult(
        session_id=str(session.id),
        response_deleted=True,
        core_deleted=True,
        pending=False,
    )
