"""AAD (Additional Authenticated Data) construction for answer revisions."""

import struct


def build_aad(
    crypto_version: int,
    envelope_id: int,
    answer_id: int,
    answer_locator: bytes,
    revision_id: int,
    revision_number: int,
) -> bytes:
    """Build canonical AAD bytes binding a revision to its database context.

    Fields are packed in fixed order: crypto_version, envelope_id, answer_id,
    answer_locator (length-prefixed), revision_id, revision_number.
    """
    locator_len = len(answer_locator)
    return struct.pack(
        f">iqqI{locator_len}sqi",
        crypto_version,
        envelope_id,
        answer_id,
        locator_len,
        answer_locator,
        revision_id,
        revision_number,
    )
