"""Resolve the stable ProjectSubject for a respondent session.

Applies the priority waterfall — identity > token > new anonymous — for open-access
entries (public slug, general link), and always returns the assigned subject for
private and authenticated links. Returns a SubjectResolutionResult with merge and
token-action instructions; the caller applies all writes before committing.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.errors import SubjectResolutionError
from app.domain.guards import ensure_present
from app.repositories.core import project_subject_identities as sub_id
from app.repositories.core import project_subjects as subjects
from app.schema.orm.core.project_subject import ProjectSubject
from app.services.public_submissions.core.resolution.subject_token import SubjectTokenService
from app.services.results import SubjectResolutionResult


class SubjectResolver:
    """Resolve the session's ProjectSubject using the priority waterfall.

    Priority for open-access (public slug / general link):
      1. Logged-in identity subject
      2. Recognition token subject
      3. New anonymous subject

    Priority for assigned-access (private / authenticated link):
      1. Assigned subject (always wins)
      2. Token used only for continuity cleanup (merge/rotate if canonical differs)

    Returns SubjectResolutionResult with final_subject_id, token_action, and optional
    merge_subject_id/merge_into_subject_id. No writes here — caller applies all effects.
    """

    def __init__(self, *, token_service: SubjectTokenService | None = None) -> None:
        self._token_service = token_service or SubjectTokenService()

    def resolve(
        self,
        db: Session,
        *,
        project_id: int,
        access_method: str,
        assigned_subject_id: UUID | None,
        token_subject_id: UUID | None,
        canonical_token_subject_id: UUID | None,
        actor_user_id: int | None,
    ) -> SubjectResolutionResult:
        """Route to assigned or open-access resolution based on access method.

        private_link and authenticated_assigned_link always use the assigned subject.
        All other access methods use the open-access waterfall.
        """
        if access_method in ("private_link", "authenticated_assigned_link"):
            return self.resolve_assigned_subject(
                db,
                project_id=project_id,
                assigned_subject_id=assigned_subject_id,
                token_subject_id=token_subject_id,
                canonical_token_subject_id=canonical_token_subject_id,
            )
        return self.resolve_for_open_access(
            db,
            project_id=project_id,
            token_subject_id=token_subject_id,
            canonical_token_subject_id=canonical_token_subject_id,
            actor_user_id=actor_user_id,
        )

    def resolve_assigned_subject(
        self,
        db: Session,
        *,
        project_id: int,
        assigned_subject_id: UUID | None,
        token_subject_id: UUID | None,
        canonical_token_subject_id: UUID | None,
    ) -> SubjectResolutionResult:
        """Assigned subject is always canonical. Token used only for continuity cleanup.

        If the token already points at the assigned canonical, keep or rotate it to canonical.
        If the token canonical differs, merge the token subject into the assigned subject and rotate.
        No token → issue a new one.
        """
        if assigned_subject_id is None:
            raise SubjectResolutionError()

        assigned = self._require_subject(db, project_id=project_id, subject_id=assigned_subject_id)
        canonical_assigned = self._resolve_to_canonical(db, project_id=project_id, subject=assigned)

        if token_subject_id is None:
            return SubjectResolutionResult(
                final_subject_id=canonical_assigned.id,
                subject_code=canonical_assigned.subject_code,
                subject_source="assigned_link",
                token_action="issue",
            )

        # Resolve token candidate to canonical before comparing.
        effective_token_subject_id = canonical_token_subject_id or token_subject_id
        if effective_token_subject_id == canonical_assigned.id:
            # Token already points at assigned canonical — keep or rotate to canonical.
            if token_subject_id == canonical_assigned.id:
                return SubjectResolutionResult(
                    final_subject_id=canonical_assigned.id,
                    subject_code=canonical_assigned.subject_code,
                    subject_source="assigned_link",
                    token_action="keep",
                )
            # Token points at a non-canonical that resolves to the same canonical.
            return SubjectResolutionResult(
                final_subject_id=canonical_assigned.id,
                subject_code=canonical_assigned.subject_code,
                subject_source="assigned_link",
                token_action="rotate",
            )

        # Token canonical differs from assigned subject — merge token into assigned.
        return SubjectResolutionResult(
            final_subject_id=canonical_assigned.id,
            subject_code=canonical_assigned.subject_code,
            subject_source="assigned_link",
            token_action="rotate",
            merge_subject_id=effective_token_subject_id,
            merge_into_subject_id=canonical_assigned.id,
        )

    def resolve_for_open_access(
        self,
        db: Session,
        *,
        project_id: int,
        token_subject_id: UUID | None,
        canonical_token_subject_id: UUID | None,
        actor_user_id: int | None,
    ) -> SubjectResolutionResult:
        """Public slug / general link resolution.

        Authority waterfall: logged-in identity > recognition token > new anonymous subject.
        If a logged-in user has no identity yet, one is created on the winning subject.
        """
        # Resolve token candidate to canonical upfront.
        effective_token_subject_id: UUID | None = None
        if token_subject_id is not None:
            effective_token_subject_id = canonical_token_subject_id or token_subject_id

        if actor_user_id is not None:
            return self._reconcile_identity_and_token(
                db,
                project_id=project_id,
                actor_user_id=actor_user_id,
                token_subject_id=token_subject_id,
                effective_token_subject_id=effective_token_subject_id,
            )

        if effective_token_subject_id is not None:
            effective_subject = self._require_subject(
                db, project_id=project_id, subject_id=effective_token_subject_id
            )
            return SubjectResolutionResult(
                final_subject_id=effective_subject.id,
                subject_code=effective_subject.subject_code,
                subject_source="recognition_token",
                token_action="mark_used",
            )

        new_subject = subjects.create_subject(db, project_id=project_id)
        return SubjectResolutionResult(
            final_subject_id=new_subject.id,
            subject_code=new_subject.subject_code,
            subject_source="anonymous_created",
            token_action="issue",
        )

    def _reconcile_identity_and_token(
        self,
        db: Session,
        *,
        project_id: int,
        actor_user_id: int,
        token_subject_id: UUID | None,
        effective_token_subject_id: UUID | None,
    ) -> SubjectResolutionResult:
        """Reconcile logged-in user identity against token candidate.

        If no identity exists: attach to the token subject (if any) or create a new subject.
        If identity exists: token same canonical → keep/rotate; token different → merge token into identity.
        Returns instructions only — no writes here.
        """
        identity = sub_id.get_active_user_identity(
            db, project_id=project_id, user_id=actor_user_id
        )

        if identity is None:
            if effective_token_subject_id is not None:
                # Attach identity to existing token subject — caller writes identity row.
                effective_subject = self._require_subject(
                    db, project_id=project_id, subject_id=effective_token_subject_id
                )
                return SubjectResolutionResult(
                    final_subject_id=effective_subject.id,
                    subject_code=effective_subject.subject_code,
                    subject_source="authenticated_user",
                    token_action="mark_used",
                    needs_identity_write=True,
                )
            # No identity, no token — create new subject, issue token, create identity.
            new_subject = subjects.create_subject(db, project_id=project_id)
            return SubjectResolutionResult(
                final_subject_id=new_subject.id,
                subject_code=new_subject.subject_code,
                subject_source="authenticated_user",
                token_action="issue",
                needs_identity_write=True,
            )

        # Identity exists — resolve it to canonical.
        identity_subject = self._require_subject(
            db, project_id=project_id, subject_id=identity.project_subject_id
        )
        canonical_identity = self._resolve_to_canonical(
            db, project_id=project_id, subject=identity_subject
        )

        if effective_token_subject_id is None:
            return SubjectResolutionResult(
                final_subject_id=canonical_identity.id,
                subject_code=canonical_identity.subject_code,
                subject_source="authenticated_user",
                token_action="issue",
            )

        if effective_token_subject_id == canonical_identity.id:
            # Token canonical same as identity canonical.
            if token_subject_id == canonical_identity.id:
                return SubjectResolutionResult(
                    final_subject_id=canonical_identity.id,
                    subject_code=canonical_identity.subject_code,
                    subject_source="authenticated_user",
                    token_action="mark_used",
                )
            # Token points at non-canonical that resolves to identity — rotate to canonical.
            return SubjectResolutionResult(
                final_subject_id=canonical_identity.id,
                subject_code=canonical_identity.subject_code,
                subject_source="authenticated_user",
                token_action="rotate",
            )

        # Token canonical differs from identity canonical — merge token subject into identity.
        return SubjectResolutionResult(
            final_subject_id=canonical_identity.id,
            subject_code=canonical_identity.subject_code,
            subject_source="authenticated_user",
            token_action="rotate",
            merge_subject_id=effective_token_subject_id,
            merge_into_subject_id=canonical_identity.id,
        )

    def _resolve_to_canonical(
        self,
        db: Session,
        *,
        project_id: int,
        subject: ProjectSubject,
    ) -> ProjectSubject:
        """Follow canonical_subject_id one level. Canonical chains are not allowed — one hop only."""
        if subject.canonical_subject_id is None:
            return subject
        return self._require_subject(
            db, project_id=project_id, subject_id=subject.canonical_subject_id
        )

    def _require_subject(
        self, db: Session, *, project_id: int, subject_id: UUID
    ) -> ProjectSubject:
        """Load a subject that must exist — a miss is a broken server invariant."""
        return ensure_present(
            subjects.get_subject(db, project_id=project_id, subject_id=subject_id),
            error=SubjectResolutionError(),
        )
