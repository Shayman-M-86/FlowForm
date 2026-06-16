"""Resolve the stable ProjectSubject for a respondent session.

Docs: docs/Policies and Services/Flows/shared/logged-in-reconciliation.md
      docs/Policies and Services/core-policies.md — Recognition token policy
      docs/Policies and Services/Logical-flow.md
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.errors import SubjectResolutionError
from app.domain.guards import ensure_present
from app.repositories.core import project_subject_identities as sub_id
from app.repositories.core import project_subjects as subjects
from app.schema.orm.core.project_subject import ProjectSubject
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User
from app.services.public_submissions.core.subject_token import SubjectTokenService
from app.services.results import ResolvedProjectSubject


class SubjectResolver:
    """Resolve the session's ProjectSubject using the priority waterfall.

    Priority:
      1. Assigned link subject (private / authenticated)
      2. Authenticated user identity + recognition token reconciliation
      3. Recognition token subject (anonymous returning browser)
      4. Newly created anonymous subject (no token, no identity)

    Docs: core-policies.md — Subject resolution order
    """

    def __init__(self, *, token_service: SubjectTokenService | None = None) -> None:
        self._token_service = token_service or SubjectTokenService()

    def resolve(
        self,
        db: Session,
        *,
        project_id: int,
        link: SurveyLink | None,
        actor: User | None,
        recognition_token: str | None = None,
    ) -> ResolvedProjectSubject:
        """Full waterfall: assigned → open-access reconciliation."""
        if link is not None and link.assigned_participant_id is not None:
            return self.resolve_assigned_subject(db, project_id=project_id, link=link)
        return self.resolve_for_open_access(
            db, project_id=project_id, actor=actor, recognition_token=recognition_token
        )

    def resolve_assigned_subject(
        self,
        db: Session,
        *,
        project_id: int,
        link: SurveyLink,
    ) -> ResolvedProjectSubject:
        """Resolve the assigned participant's ProjectSubject from a private/authenticated link.

        Errors if the link has no assigned_participant_id or the subject row is missing.
        Docs: Private-link-access-Flow.md §6, Authenticated-link-access-Flow.md §8
        """
        participant = ensure_present(link.assigned_participant, error=SubjectResolutionError())
        subject = self._require_subject(db, project_id=project_id, subject_id=participant.project_subject_id)
        return ResolvedProjectSubject(subject=subject, source="assigned_link")

    def resolve_for_open_access(
        self,
        db: Session,
        *,
        project_id: int,
        actor: User | None,
        recognition_token: str | None,
    ) -> ResolvedProjectSubject:
        """Resolve subject for public slug / general link access.

        Runs logged-in reconciliation first, then falls back to token lookup,
        then creates a new anonymous subject.
        Docs: shared/logged-in-reconciliation.md, Logical-flow.md
        """
        token_subject: ProjectSubject | None = None
        if recognition_token:
            token_subject = self._token_service.lookup(
                db, project_id=project_id, raw_token=recognition_token
            )

        if actor is not None:
            return self.reconcile_identity_and_token(
                db,
                project_id=project_id,
                actor=actor,
                token_subject=token_subject,
            )

        if token_subject is not None:
            return ResolvedProjectSubject(subject=token_subject, source="recognition_token")

        subject = subjects.create_subject(db, project_id=project_id)
        return ResolvedProjectSubject(subject=subject, source="anonymous_created")

    def reconcile_identity_and_token(
        self,
        db: Session,
        *,
        project_id: int,
        actor: User,
        token_subject: ProjectSubject | None,
    ) -> ResolvedProjectSubject:
        """Reconcile a logged-in user identity against an existing token subject.

        Implements the 7-case table from Logical-flow.md:

          no identity + no token  → create subject, create user identity
          no identity + token     → attach user identity to token subject
          identity + no token     → use identity subject
          identity + same token   → use identity subject
          identity + diff token   → merge token subject into identity subject
                                    via canonical_subject_id; rotate token

        Docs: shared/logged-in-reconciliation.md, core-policies.md — Token/identity conflict
        """
        identity = sub_id.get_active_user_identity(db, project_id=project_id, user_id=actor.id)

        if identity is None:
            if token_subject is not None:
                # Attach the logged-in user to the existing token subject.
                sub_id.create_user_identity(
                    db,
                    project_id=project_id,
                    project_subject_id=token_subject.id,
                    user=actor,
                )
                self._token_service.rotate(db, project_id=project_id, subject=token_subject)
                return ResolvedProjectSubject(subject=token_subject, source="authenticated_user")
            else:
                # Brand new: create subject and attach identity.
                subject = subjects.create_subject(db, project_id=project_id)
                sub_id.create_user_identity(
                    db, project_id=project_id, project_subject_id=subject.id, user=actor
                )
                return ResolvedProjectSubject(subject=subject, source="authenticated_user")

        # Identity exists — it is canonical.
        identity_subject = self._require_subject(
            db, project_id=project_id, subject_id=identity.project_subject_id
        )

        if token_subject is not None and token_subject.id != identity_subject.id:
            # Token subject differs from identity subject — merge it in.
            subjects.set_canonical_subject(
                db, subject=token_subject, canonical=identity_subject
            )
            self._token_service.rotate(db, project_id=project_id, subject=identity_subject)

        return ResolvedProjectSubject(subject=identity_subject, source="authenticated_user")

    def _require_subject(self, db: Session, *, project_id: int, subject_id: UUID) -> ProjectSubject:
        """Load a subject that must exist — a miss is a broken server invariant."""
        return ensure_present(
            subjects.get_subject(db, project_id=project_id, subject_id=subject_id),
            error=SubjectResolutionError(),
        )
