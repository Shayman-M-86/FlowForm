"""App-aware locator operations.

Locators are deterministic pseudonymous identifiers derived from a session ID
and a linkage key. They let the response database reference sessions and
answers without storing real identifiers.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.crypto._internal.linkage_keys import (
    get_current_linkage_key,
    get_linkage_key_by_version,
)
from app.crypto._internal.locators import (
    derive_answer_locator as _derive_answer_locator,
)
from app.crypto._internal.locators import (
    derive_session_locator as _derive_session_locator,
)
from app.crypto.models import AnswerLocator, LinkageKey, NewSessionLocator, SessionLocator


def load_current_linkage_key(db: Session) -> LinkageKey:
    """Return the active linkage key."""
    return get_current_linkage_key(db)


def resolve_new_session_locator(db: Session, session_id: UUID) -> NewSessionLocator:
    """Resolve the current linkage key and derive a new session locator.

    Uses the current AWSCURRENT linkage key and returns the derived
    locator alongside the key version for storage.
    """
    key = get_current_linkage_key(db)
    locator = SessionLocator(_derive_session_locator(session_id, key.secret))

    new_locator = NewSessionLocator(
        linkage_key_version=key.version,
        session_locator=locator,
    )

    return new_locator


def derive_session_locator(session_id: UUID, linkage_key: LinkageKey) -> NewSessionLocator:
    """Derive a session locator with a caller-supplied linkage key."""
    locator = SessionLocator(_derive_session_locator(session_id, linkage_key.secret))
    return NewSessionLocator(
        linkage_key_version=linkage_key.version,
        session_locator=locator,
    )


def resolve_existing_session_locator(
    db: Session,
    session_id: UUID,
    linkage_key_version: int,
) -> tuple[SessionLocator, LinkageKey]:
    """Re-derive a session locator for a returning submission.

    Looks up the historical linkage key so the same locator is
    produced as when the session was first created.
    """
    key = get_linkage_key_by_version(linkage_key_version, db)
    return SessionLocator(_derive_session_locator(session_id, key.secret)), key


def derive_answer_locator(
    session_id: UUID,
    question_node_id: UUID,
    linkage_key: LinkageKey,
) -> AnswerLocator:
    """Derive an answer locator with a caller-supplied linkage key."""
    return AnswerLocator(_derive_answer_locator(session_id, question_node_id, linkage_key.secret))


def resolve_answer_locator(
    db: Session,
    session_id: UUID,
    linkage_key_version: int,
    question_node_id: UUID,
) -> AnswerLocator:
    """Resolve the historical linkage key and derive one answer locator.

    Used for storing or looking up an encrypted answer in the
    response database.
    """
    key = get_linkage_key_by_version(linkage_key_version, db)
    return AnswerLocator(_derive_answer_locator(session_id, question_node_id, key.secret))


def resolve_answer_locators(
    db: Session,
    session_id: UUID,
    linkage_key_version: int,
    question_node_ids: list[UUID],
) -> dict[UUID, AnswerLocator]:
    """Resolve the historical linkage key and derive answer locators.

    Fetches the linkage key once and derives a locator per question,
    avoiding repeated key lookups.
    """
    key = get_linkage_key_by_version(linkage_key_version, db)

    locators = {
        question_node_id: AnswerLocator(_derive_answer_locator(session_id, question_node_id, key.secret))
        for question_node_id in question_node_ids
    }

    return locators
