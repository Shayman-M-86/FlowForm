"""Recognition token lifecycle: lookup, issue, rotate, apply.

Tokens link a returning browser to a stable ProjectSubject without authentication.
Only the hash is stored; the raw token travels only in cookies and return values.
Lookup never touches last_used_at — the caller decides whether to mark the token used.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.core import project_subject_tokens as sub_tok
from app.services.results import RecognitionTokenLookupResult, TokenAction


class SubjectTokenService:
    """Manage recognition tokens scoped to a project.

    A recognition token links a returning browser to a stable ProjectSubject
    without requiring authentication. Only the hash is stored — the raw token
    is never persisted.

    Token lookup is used on public slug and general link access.
    Private and authenticated links always resolve via the assigned subject;
    the token is only checked for continuity cleanup (merge/rotate).
    """

    def lookup(
        self,
        db: Session,
        *,
        project_id: int,
        raw_token: str,
    ) -> RecognitionTokenLookupResult:
        """Return token candidate metadata only. Does not update last_used_at.

        SubjectResolver calls this before deciding the final subject. Whether to
        mark the token used is determined by the resolved token_action, applied
        later via apply_token_action.
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

        issue   — create a new token for final_subject_id; return raw token.
        rotate  — revoke any existing token for final_subject_id, issue a new
                  one; return raw token.
        mark_used — update last_used_at on the existing token; return
                    existing_raw_token so the caller re-sets the cookie.
        keep / none — no write; return None (browser cookie unchanged).
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
