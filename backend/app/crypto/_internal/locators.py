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
    slot_id: UUID,
    linkage_secret: bytes,
) -> bytes:
    """Derive an opaque answer locator from a core answer slot ID."""
    return hmac.new(
        key=linkage_secret,
        msg=slot_id.bytes,
        digestmod=hashlib.sha256,
    ).digest()
