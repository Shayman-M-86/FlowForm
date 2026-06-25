"""Reconcile committed core sessions that are missing response envelopes.

Scans in-progress core sessions, derives session locators, checks the
response DB for matching envelopes, and marks missing-envelope sessions
as abandoned.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.orm import Session

from app.crypto import get_crypto_services
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_envelope_repo

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReconciliationResult:
    """Counts and safe identifiers for operator review."""

    scanned: int = 0
    abandoned: int = 0
    matched: int = 0
    errors: int = 0
    abandoned_session_ids: list[UUID] = field(default_factory=list)


def reconcile_orphaned_sessions(
    db: Session,
    response_db: Session,
) -> ReconciliationResult:
    """Mark committed core sessions without response envelopes as abandoned."""
    loc_svc = get_crypto_services().locator_service

    sessions = ssr.get_in_progress_sessions(db)

    result = ReconciliationResult(scanned=len(sessions))

    for session in sessions:
        try:
            session_locator, _ = loc_svc.for_existing_session(
                session.id, session.linkage_key_version, db,
            )

            envelope = response_envelope_repo.get_by_locator(
                response_db, session_locator,
            )

            if envelope is not None:
                result.matched += 1
                continue

            ssr.mark_abandoned(db, submission_session=session)
            result.abandoned += 1
            result.abandoned_session_ids.append(session.id)

            logger.warning(
                "reconciliation.session_marked_abandoned",
                extra={"session_id": str(session.id)},
            )

        except Exception:
            result.errors += 1
            logger.error(
                "reconciliation.session_check_failed",
                extra={"session_id": str(session.id)},
                exc_info=True,
            )

    db.commit()

    logger.info(
        "reconciliation.complete",
        extra={
            "scanned": result.scanned,
            "abandoned": result.abandoned,
            "matched": result.matched,
            "errors": result.errors,
        },
    )

    return result
