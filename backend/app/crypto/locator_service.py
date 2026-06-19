"""Service for deriving opaque locators that link Core DB to Response DB records."""

from __future__ import annotations

from dataclasses import dataclass

from app.crypto.linkage_key_service import LinkageKeyService
from app.crypto.locators import derive_answer_locator, derive_session_locator


@dataclass(frozen=True, slots=True)
class NewSessionLocator:
    """Returned when deriving a locator for a brand-new session."""

    linkage_key_version: int
    session_locator: bytes


class LocatorService:
    """Derives opaque locators from stable Core DB IDs using linkage secrets."""

    def __init__(self, linkage_key_service: LinkageKeyService) -> None:
        self._keys = linkage_key_service

    def for_new_session(self, session_id: str) -> NewSessionLocator:
        """Derive a session locator using the current linkage key."""
        key = self._keys.get_linkage_key()
        locator = derive_session_locator(session_id, key.secret)
        return NewSessionLocator(
            linkage_key_version=key.version,
            session_locator=locator,
        )

    def for_existing_session(
        self, session_id: str, linkage_key_version: int
    ) -> bytes:
        """Derive a session locator using a stored linkage key version."""
        key = self._keys.get_linkage_key_by_version(linkage_key_version)
        return derive_session_locator(session_id, key.secret)

    def answer_locator(
        self,
        session_id: str,
        question_node_id: str,
        linkage_key_version: int,
    ) -> bytes:
        """Derive a single answer locator."""
        key = self._keys.get_linkage_key_by_version(linkage_key_version)
        return derive_answer_locator(session_id, question_node_id, key.secret)

    def answer_locators(
        self,
        session_id: str,
        question_node_ids: list[str],
        linkage_key_version: int,
    ) -> dict[str, bytes]:
        """Derive answer locators for multiple questions in one call."""
        key = self._keys.get_linkage_key_by_version(linkage_key_version)
        return {
            qid: derive_answer_locator(session_id, qid, key.secret)
            for qid in question_node_ids
        }
