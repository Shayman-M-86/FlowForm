from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.errors import SubjectResolutionError
from app.domain.guards import ensure_present
from app.repositories.core import project_subject_identities as sub_id
from app.repositories.core import project_subject_tokens as sub_tok
from app.repositories.core import project_subjects as subjects
from app.schema.orm.core.project_subject import ProjectSubject
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User
from app.services.results import ResolvedProjectSubject


class ProjectSubjectResolver:
    """Resolve the optional stable subject using only server-owned context."""

    def resolve(
        self,
        db: Session,
        *,
        project_id: int,
        link: SurveyLink | None,
        actor: User | None,
        recognition_token: str | None = None,
        create_anonymous_subject: bool = False,
    ) -> ResolvedProjectSubject:
        
        if link is not None and link.assigned_participant_id is not None:
            participant = ensure_present( link.assigned_participant, error=SubjectResolutionError())
            subject = self._require_subject(db, project_id=project_id, subject_id=participant.project_subject_id)
            return ResolvedProjectSubject(subject=subject, source="assigned_link")

        if actor is not None and (
            identity := sub_id.get_active_user_identity(
                db,
                project_id=project_id,
                user_id=actor.id,
            )
        ) is not None:
            subject = self._require_subject(
                db,
                project_id=project_id,
                subject_id=identity.project_subject_id,
            )
            return ResolvedProjectSubject(subject=subject, source="authenticated_user")

        if recognition_token and (
            token := sub_tok.get_active_token(db, project_id=project_id,raw_token=recognition_token)
        ) is not None:
            subject = self._require_subject(db, project_id=project_id, subject_id=token.project_subject_id)
            sub_tok.mark_used(db, token=token)
            return ResolvedProjectSubject(subject=subject, source="recognition_token")

        if create_anonymous_subject:
            subject = subjects.create_subject(db, project_id=project_id)
            return ResolvedProjectSubject(subject=subject, source="anonymous_created")

        return ResolvedProjectSubject(subject=None, source="none")

    def _require_subject(self, db: Session, *, project_id: int, subject_id: UUID) -> ProjectSubject:
        """Resolve a subject referenced by server-owned context.

        A link, identity, or token that names a subject must resolve to a real
        row. A miss is a broken server invariant, not a reason to silently
        downgrade a known respondent to an anonymous session.
        """
        subject = subjects.get_subject(
            db,
            project_id=project_id,
            subject_id=subject_id,
        )
        return ensure_present(subject, error=SubjectResolutionError())