"""Deterministic locator derivation using HMAC-SHA256."""

import hashlib
import hmac
from uuid import UUID


def derive_session_locator(core_session_id: UUID, linkage_secret: bytes) -> bytes:
    """Derive an opaque session locator from a core session ID."""
    return hmac.new(
        key=linkage_secret,
        msg=core_session_id.bytes,
        digestmod=hashlib.sha256,
    ).digest()


def derive_answer_locator(
    core_session_id: UUID,
    question_node_id: UUID,
    linkage_secret: bytes,
) -> bytes:
    """Derive an opaque answer locator from a core session ID and question node ID."""
    msg = core_session_id.bytes + question_node_id.bytes
    return hmac.new(
        key=linkage_secret,
        msg=msg,
        digestmod=hashlib.sha256,
    ).digest()
