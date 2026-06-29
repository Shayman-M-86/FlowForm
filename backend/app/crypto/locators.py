"""App-aware locator operations.

Locators are deterministic pseudonymous identifiers derived from a session ID
and a linkage key. They let the response database reference sessions and
answers without storing real identifiers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from app.cache import AppCache
    from app.crypto._internal.client_extension import CryptoClients


def load_current_linkage_key(
    db: Session,
    *,
    cache: AppCache,
    clients: CryptoClients,
) -> LinkageKey:
    """Return the active linkage key."""
    return get_current_linkage_key(db, cache=cache, clients=clients)


def resolve_new_session_locator(
    db: Session,
    session_id: UUID,
    *,
    cache: AppCache,
    clients: CryptoClients,
) -> NewSessionLocator:
    """Resolve the current linkage key and derive a new session locator.

    Uses the current AWSCURRENT linkage key and returns the derived
    locator alongside the key version for storage.
    """
    key = get_current_linkage_key(db, cache=cache, clients=clients)
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
    *,
    cache: AppCache,
    clients: CryptoClients,
) -> tuple[SessionLocator, LinkageKey]:
    """Re-derive a session locator for a returning submission.

    Looks up the historical linkage key so the same locator is
    produced as when the session was first created.
    """
    key = get_linkage_key_by_version(linkage_key_version, db, cache=cache, clients=clients)
    return SessionLocator(_derive_session_locator(session_id, key.secret)), key


def derive_answer_locator(
    slot_id: UUID,
    linkage_key: LinkageKey,
) -> AnswerLocator:
    """Derive an answer locator from a core submission answer slot ID."""
    return AnswerLocator(_derive_answer_locator(slot_id, linkage_key.secret))


def resolve_answer_locator(
    db: Session,
    slot_id: UUID,
    linkage_key_version: int,
    *,
    cache: AppCache,
    clients: CryptoClients,
) -> AnswerLocator:
    """Resolve the historical linkage key and derive one answer locator."""
    key = get_linkage_key_by_version(linkage_key_version, db, cache=cache, clients=clients)
    return AnswerLocator(_derive_answer_locator(slot_id, key.secret))


def resolve_answer_locators(
    db: Session,
    linkage_key_version: int,
    slot_ids: list[UUID],
    *,
    cache: AppCache,
    clients: CryptoClients,
) -> dict[UUID, AnswerLocator]:
    """Resolve the historical linkage key and derive answer locators for slots."""
    key = get_linkage_key_by_version(linkage_key_version, db, cache=cache, clients=clients)
    return {slot_id: AnswerLocator(_derive_answer_locator(slot_id, key.secret)) for slot_id in slot_ids}
