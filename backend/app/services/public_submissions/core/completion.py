"""Session completion service.

Loads and decrypts latest answers, validates completeness, and marks the
core session as completed. Idempotent: a repeated call returns the stored
completion state without duplicate writes.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.crypto import (
    build_aad,
    decrypt_answer,
    parse_plaintext_payload,
    unwrap_dek,
)
from app.crypto.dek_cache import DekCache
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import SessionInvalidError
from app.repositories.core import submission_events as event_repo
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_answer_repo, response_answer_revision_repo
from app.services.public_submissions.core.session_loader import SessionContext

logger = logging.getLogger(__name__)

_KMS_CONTEXT_VERSION = 1


@dataclass(frozen=True, slots=True)
class CompletionResult:
    """Outcome returned to the caller on successful completion."""

    session_id: str
    status: str
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class DecryptedAnswer:
    """One decrypted answer mapped to its question node ID."""

    question_node_id: str
    answer_state: str
    answer_value: Any | None


class CompletionService:
    """Orchestrates session completion per doc 03 §5."""

    def __init__(self, *, dek_cache: DekCache | None = None) -> None:
        self._dek_cache = dek_cache

    def complete_session(
        self,
        db: Session,
        response_db: Session,
        *,
        ctx: SessionContext,
    ) -> CompletionResult:
        """Complete a session. Idempotent — returns stored state if already completed."""
        # Idempotent check: if already completed, return stored state immediately
        if ctx.session.session_status == "completed":
            return CompletionResult(
                session_id=str(ctx.session.id),
                status="completed",
                completed_at=ctx.session.completed_at,  # type: ignore[arg-type]
            )

        # Lock the session for mutation
        locked_session = ssr.lock_for_update(db, ctx.session.id)
        if locked_session is None:
            raise SessionInvalidError("Session disappeared during completion.")
        if locked_session.session_status != "in_progress":
            raise SessionInvalidError(f"Session is {locked_session.session_status}.")

        # Load and decrypt all latest revisions
        decrypted_answers = self._load_and_decrypt_answers(response_db, ctx)

        # Validate completion requirements
        self._validate_completion(db, ctx, decrypted_answers)

        # Mark session completed
        now = datetime.now(UTC)
        ssr.mark_completed(db, submission_session=locked_session, completed_at=now)

        # Insert completion event — non-fatal on failure
        try:
            event_repo.create_event(
                db,
                session_id=ctx.session.id,
                survey_version_id=ctx.survey_version.id,
                event_type="session_completed",
            )
        except Exception:
            logger.warning("completion.event_create_failed", exc_info=True)

        commit_with_err_handle(db, contexts=[])

        return CompletionResult(
            session_id=str(ctx.session.id),
            status="completed",
            completed_at=now,
        )

    def _load_and_decrypt_answers(
        self,
        response_db: Session,
        ctx: SessionContext,
    ) -> list[DecryptedAnswer]:
        plaintext_dek = self._get_or_unwrap_dek(ctx)
        answers = response_answer_repo.get_all_by_envelope(response_db, ctx.envelope.id)

        decrypted: list[DecryptedAnswer] = []
        for answer in answers:
            latest_rev = response_answer_revision_repo.get_latest(response_db, answer.id)
            if latest_rev is None:
                continue

            aad = build_aad(
                crypto_version=ctx.envelope.crypto_version,
                envelope_id=answer.envelope_id,
                answer_id=answer.id,
                answer_locator=answer.answer_locator,
                revision_id=latest_rev.id,
                revision_number=latest_rev.revision_number,
            )
            plaintext_bytes = decrypt_answer(
                latest_rev.ciphertext, plaintext_dek, latest_rev.nonce, aad
            )
            parsed = parse_plaintext_payload(plaintext_bytes)

            decrypted.append(
                DecryptedAnswer(
                    question_node_id=parsed["question_node_id"],
                    answer_state=parsed["answer_state"],
                    answer_value=parsed["answer_value"],
                )
            )

        return decrypted

    def _validate_completion(
        self,
        db: Session,
        ctx: SessionContext,
        decrypted_answers: list[DecryptedAnswer],
    ) -> None:
        from sqlalchemy import select

        from app.domain.survey_answer_validation import (
            DecryptedAnswer as ValidationAnswer,
        )
        from app.domain.survey_answer_validation import (
            QuestionNode,
            RuleNode,
            validate_submission,
        )
        from app.schema.orm.core.survey_content import SurveyQuestion

        all_nodes = db.scalars(
            select(SurveyQuestion).where(
                SurveyQuestion.survey_version_id == ctx.survey_version.id,
            )
        ).all()

        questions = [
            QuestionNode(
                node_id=str(n.id),
                family=(n.question_schema or {}).get("family"),
                sort_key=n.sort_key,
            )
            for n in all_nodes
            if n.node_type == "question"
        ]
        rules = [
            RuleNode(sort_key=n.sort_key, rule_schema=n.question_schema or {})
            for n in all_nodes
            if n.node_type == "rule"
        ]
        validation_answers = [
            ValidationAnswer(
                question_node_id=a.question_node_id,
                answer_state=a.answer_state,
                answer_value=a.answer_value,
            )
            for a in decrypted_answers
        ]

        validate_submission(questions, rules, validation_answers)

    def _get_or_unwrap_dek(self, ctx: SessionContext) -> bytes:
        if self._dek_cache is not None:
            cached = self._dek_cache.get(ctx.session_locator)
            if cached is not None:
                return cached

        enc = ctx.encryption_settings
        kms_context = {
            "session_locator": ctx.session_locator.hex(),
            "kms_context_version": str(_KMS_CONTEXT_VERSION),
        }
        plaintext_dek = unwrap_dek(
            ctx.envelope.wrapped_dek,
            ctx.envelope.kms_key_arn,
            kms_context,
            region=enc.aws_region,
            access_key_id=enc.aws_access_key_id,
            secret_access_key=enc.aws_secret_access_key,
        )

        if self._dek_cache is not None:
            self._dek_cache.put(ctx.session_locator, plaintext_dek)

        return plaintext_dek
