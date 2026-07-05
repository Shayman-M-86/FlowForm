"""AAD (Additional Authenticated Data) construction for encrypted answers."""

from __future__ import annotations

import struct

from app.crypto.models import AnswerContext, SessionDEKContext


def build_aad(ctx: AnswerContext) -> bytes:
    """Build canonical AAD bytes binding an answer to its database context."""
    locator_len = len(ctx.answer_locator)
    return struct.pack(
        f">i16sI{locator_len}s",
        ctx.crypto_version,
        ctx.envelope_id.bytes,
        locator_len,
        ctx.answer_locator,
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
