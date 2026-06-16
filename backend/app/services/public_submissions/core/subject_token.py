"""Recognition token lifecycle: lookup, issue, rotate, apply.

Docs: docs/Policies and Services/core-policies.md — Recognition token policy
      docs/Policies and Services/Flows/shared/check-recognition-token.md
      docs/Policies and Services/Flows/shared/issue-or-rotate-recognition-token.md
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.core import project_subject_tokens as sub_tok
from app.schema.orm.core.project_subject import ProjectSubject
from app.services.results import RecognitionTokenLookupResult, TokenAction


class SubjectTokenService:
    """Manage recognition tokens scoped to a project.

    A recognition token links a returning browser to a stable ProjectSubject
    without requiring authentication. Only the hash is stored — the raw token
    is never persisted.

    Token lookup is valid only on public slug and general link access.
    Private and authenticated links use the assigned subject as canonical.
    Docs: core-policies.md — Token use by access method
    """

    def lookup(
        self,
        db: Session,
        *,
        project_id: int,
        raw_token: str,
    ) -> RecognitionTokenLookupResult:
        """Return token candidate metadata only. Does not update last_used_at.

        Caller (SubjectResolver) decides whether to mark the token used.
        Docs: shared/check-recognition-token.md
        """
        token = sub_tok.get_active_token(db, project_id=project_id, raw_token=raw_token)
        if token is None:
            return RecognitionTokenLookupResult(
                token_present=True,
                token_valid=False,
                invalid_reason="not_found_or_expired",
            )
        canonical_id = (
            token.subject.canonical_subject_id
            if token.subject.canonical_subject_id is not None
            else None
        )
        return RecognitionTokenLookupResult(
            token_present=True,
            token_valid=True,
            token_id=token.id,
            token_subject_id=token.subject.id,
            canonical_token_subject_id=canonical_id,
        )

    def issue(
        self,
        db: Session,
        *,
        project_id: int,
        subject: ProjectSubject,
    ) -> str:
        """Return a raw recognition token for subject, issuing a new one only if needed.

        If a valid token already exists for this subject, returns a newly issued token
        anyway — callers should treat the return value as the canonical current token.
        Docs: core-policies.md — Issuing tokens
        """
        _, raw_token = sub_tok.create_token(
            db, project_id=project_id, project_subject_id=subject.id
        )
        return raw_token

    def rotate(
        self,
        db: Session,
        *,
        project_id: int,
        subject: ProjectSubject,
    ) -> str:
        """Revoke any existing token for subject and issue a fresh one. Returns raw token.

        Called after token/identity reconciliation so the browser's next request
        resolves directly to the canonical subject.
        Docs: shared/logged-in-reconciliation.md — After reconciliation
        """
        existing = sub_tok.get_active_token_for_subject(
            db, project_id=project_id, project_subject_id=subject.id
        )
        if existing is not None:
            sub_tok.revoke_token(db, token=existing)
        _, raw_token = sub_tok.create_token(
            db, project_id=project_id, project_subject_id=subject.id
        )
        return raw_token

    def apply_token_action(
        self,
        db: Session,
        *,
        project_id: int,
        final_subject_id: UUID,
        token_action: TokenAction,
        existing_raw_token: str | None = None,
    ) -> str | None:
        """Apply the token_action instruction from SubjectResolutionResult.

        Returns the raw token only when the browser cookie must change (issue or rotate),
        or returns the existing raw token for mark_used (caller re-sets cookie).
        Returns None for keep and none.

        Docs: shared/issue-or-rotate-recognition-token.md
        """
        if token_action == "issue":
            _, raw_token = sub_tok.create_token(
                db, project_id=project_id, project_subject_id=final_subject_id
            )
            return raw_token

        if token_action == "rotate":
            existing = sub_tok.get_active_token_for_subject(
                db, project_id=project_id, project_subject_id=final_subject_id
            )
            if existing is not None:
                sub_tok.revoke_token(db, token=existing)
            _, raw_token = sub_tok.create_token(
                db, project_id=project_id, project_subject_id=final_subject_id
            )
            return raw_token

        if token_action == "mark_used":
            token_row = sub_tok.get_active_token_for_subject(
                db, project_id=project_id, project_subject_id=final_subject_id
            )
            if token_row is not None:
                sub_tok.mark_used(db, token=token_row)
            return existing_raw_token

        # "keep" or "none": browser cookie unchanged, no raw token returned.
        return None
