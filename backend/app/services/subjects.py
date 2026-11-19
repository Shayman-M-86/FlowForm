from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.db.error_handling import RuleContext, commit_with_err_handle
from app.domain.errors import SubjectNotFoundError
from app.domain.guards import ensure_present
from app.repositories.core import project_subjects as psr
from app.repositories.core.project_subjects import SubjectListRow
from app.schema.api.requests.subjects import UpdateSubjectRequest
from app.schema.enums import CanonicalSubjectFilter
from app.schema.orm.core.project_subject import ProjectSubject
from app.schema.types import Count, ParticipantId, ProjectId, SearchText, SubjectId


class SubjectService:
    """Service for project subject read and update operations."""

    def list_subjects(
        self,
        db: Session,
        *,
        project_id: ProjectId,
        canonical_status: CanonicalSubjectFilter = "canonical",
        is_participant: bool | None = None,
        search: SearchText | None = None,
        offset: Count = 0,
        limit: Count = 50,
    ) -> tuple[Sequence[SubjectListRow], Count]:
        return psr.list_subjects(
            db,
            project_id=project_id,
            canonical_status=canonical_status,
            is_participant=is_participant,
            search=search,
            offset=offset,
            limit=limit,
        )

    def get_subject(
        self,
        db: Session,
        *,
        project_id: ProjectId,
        subject_id: SubjectId,
    ) -> tuple[ProjectSubject, ParticipantId | None]:
        result = psr.get_subject_with_participant(db, project_id=project_id, subject_id=subject_id)
        return ensure_present(result, error=SubjectNotFoundError())

    def update_subject(
        self,
        db: Session,
        *,
        project_id: ProjectId,
        subject_id: SubjectId,
        data: UpdateSubjectRequest,
    ) -> tuple[ProjectSubject, ParticipantId | None]:
        subject, participant_id = self.get_subject(db, project_id=project_id, subject_id=subject_id)
        psr.set_subject_code(db, subject=subject, subject_code=data.subject_code)
        contexts: list[RuleContext] = [subject]
        commit_with_err_handle(db, contexts=contexts)
        return subject, participant_id
