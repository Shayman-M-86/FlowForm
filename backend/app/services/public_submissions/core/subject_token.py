"""Recognition token lifecycle: lookup, issue, rotate.

Docs: docs/Policies and Services/core-policies.md — Recognition token policy
      docs/Policies and Services/Flows/shared/check-recognition-token.md
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.core import project_subject_tokens as sub_tok
from app.schema.orm.core.project_subject import ProjectSubject


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
    ) -> ProjectSubject | None:
        """Return the ProjectSubject for a valid recognition token, or None.

        Returns None if the token is missing, expired, or revoked.
        Updates last_used_at on a successful lookup.
        Docs: shared/check-recognition-token.md
        """
        token = sub_tok.get_active_token(db, project_id=project_id, raw_token=raw_token)
        if token is None:
            return None
        sub_tok.mark_used(db, token=token)
        return token.subject

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
