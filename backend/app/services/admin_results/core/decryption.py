"""Answer locator resolution and decryption for admin results.

Isolates the cross-DB read + decrypt step: resolve each slot's stable answer
locator, fetch any stored ciphertext from the response DB, and (when requested)
decrypt it under the session's envelope key. Callers receive a single
``ResolvedAnswers`` bundle they can index per slot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.crypto.answers import decrypt_answer_current
from app.crypto.locators import resolve_answer_locators
from app.crypto.models import AnswerContext, AnswerLocator
from app.crypto.session_key import load_session_envelope_crypto_context
from app.repositories.response import response_answer_repo
from app.schema.orm.core.submission_answer_slot import SubmissionAnswerSlot
from app.schema.orm.core.submission_session import SubmissionSession

if TYPE_CHECKING:
    from app.cache import AppCache
    from app.crypto._internal.client_extension import CryptoClients


@dataclass(frozen=True, slots=True)
class ResolvedAnswers:
    """Per-slot locators plus the ciphertext/plaintext found for them.

    ``locators`` maps slot id -> stable answer locator. ``found`` and
    ``decrypted_by_locator`` are keyed by the raw locator bytes; the latter is
    empty unless decryption was requested.
    """

    locators: dict[UUID, AnswerLocator]
    found: dict[bytes, Any]
    decrypted_by_locator: dict[bytes, Any]


def resolve_and_decrypt_answers(
    db: Session,
    response_db: Session,
    *,
    session: SubmissionSession,
    slots: list[SubmissionAnswerSlot],
    include_decrypted_answer_values: bool,
    cache: AppCache,
    clients: CryptoClients,
) -> ResolvedAnswers:
    """Resolve slot locators, fetch stored answers, and optionally decrypt them."""
    locators = resolve_answer_locators(
        db,
        session.linkage_key_version,
        [slot.id for slot in slots],
        cache=cache,
        clients=clients,
    )
    found = {
        answer.answer_locator: answer
        for answer in response_answer_repo.get_by_locators(response_db, list(locators.values()))
    }

    decrypted_by_locator: dict[bytes, Any] = {}
    if include_decrypted_answer_values and found:
        ectx = load_session_envelope_crypto_context(
            db, response_db, session=session, cache=cache, clients=clients
        )
        for raw_locator, answer in found.items():
            decrypted_by_locator[raw_locator] = decrypt_answer_current(
                ciphertext=answer.ciphertext,
                nonce=answer.nonce,
                context=AnswerContext(
                    dek=ectx.plaintext_key,
                    crypto_version=ectx.envelope.crypto_version,
                    envelope_id=answer.envelope_id,
                    answer_locator=AnswerLocator(answer.answer_locator),
                ),
            )

    return ResolvedAnswers(locators=locators, found=found, decrypted_by_locator=decrypted_by_locator)
