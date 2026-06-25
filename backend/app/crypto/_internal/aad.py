"""AAD (Additional Authenticated Data) construction for answer revisions."""

from __future__ import annotations

import struct

from app.crypto.models import RevisionContext, SessionDEKContext


def build_aad(ctx: RevisionContext) -> bytes:
    """Build canonical AAD bytes binding a revision to its database context.

    Fields are packed in fixed order: crypto_version, envelope_id (16 bytes),
    answer_id (16 bytes), answer_locator (length-prefixed), revision_id
    (16 bytes), revision_number.
    """
    locator_len = len(ctx.answer_locator)
    return struct.pack(
        f">i16s16sI{locator_len}s16si",
        ctx.crypto_version,
        ctx.envelope_id.bytes,
        ctx.answer_id.bytes,
        locator_len,
        ctx.answer_locator,
        ctx.revision_id.bytes,
        ctx.revision_number,
    )


def build_session_dek_wrap_aad(ctx: SessionDEKContext) -> bytes:
    """Build canonical AAD bytes binding a session DEK wrap to its survey.

    Fields are packed in fixed order: crypto_version, project_id, survey_id,
    session_id (16 bytes), session_locator (length-prefixed).
    """
    locator_len = len(ctx.session_locator)
    return struct.pack(
        f">iqq16sI{locator_len}s",
        ctx.crypto_version,
        ctx.project_id,
        ctx.survey_id,
        ctx.session_id.bytes,
        locator_len,
        ctx.session_locator,
    )
