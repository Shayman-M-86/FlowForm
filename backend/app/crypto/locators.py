"""Deterministic locator derivation using HMAC-SHA256."""

import hashlib
import hmac


def derive_session_locator(core_session_id: str, linkage_secret: bytes) -> bytes:
    """Derive an opaque session locator from a core session ID."""
    return hmac.new(
        key=linkage_secret,
        msg=core_session_id.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()


def derive_answer_locator(
    core_session_id: str,
    question_node_id: str,
    linkage_secret: bytes,
) -> bytes:
    """Derive an opaque answer locator from a core session ID and question node ID."""
    msg = f"{core_session_id}:{question_node_id}".encode()
    return hmac.new(
        key=linkage_secret,
        msg=msg,
        digestmod=hashlib.sha256,
    ).digest()
