"""AAD (Additional Authenticated Data) construction for answer revisions."""

from __future__ import annotations

import struct
import uuid


def build_aad(
    crypto_version: int,
    envelope_id: uuid.UUID,
    answer_id: uuid.UUID,
    answer_locator: bytes,
    revision_id: uuid.UUID,
    revision_number: int,
) -> bytes:
    """Build canonical AAD bytes binding a revision to its database context.

    Fields are packed in fixed order: crypto_version, envelope_id (16 bytes),
    answer_id (16 bytes), answer_locator (length-prefixed), revision_id
    (16 bytes), revision_number.
    """
    locator_len = len(answer_locator)
    return struct.pack(
        f">i16s16sI{locator_len}s16si",
        crypto_version,
        envelope_id.bytes,
        answer_id.bytes,
        locator_len,
        answer_locator,
        revision_id.bytes,
        revision_number,
    )
