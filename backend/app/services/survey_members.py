from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain.errors import (
    MemberNotFoundError,
    SurveyMemberRoleAlreadyAssignedError,
    SurveyMemberRoleNotFoundError,
    SurveyNotFoundError,
    SurveyRoleNotFoundError,
)
from app.domain.guards import ensure_present
from app.repositories import members_repo as mr
from app.repositories import survey_members_repo as smr
from app.repositories import survey_roles_repo as srr
from app.repositories import surveys_repo as sr
from app.schema.api.requests.surveys_access import AssignSurveyMemberRoleRequest, UpdateSurveyMemberRoleRequest
from app.schema.orm.core.survey_access import SurveyMembershipRole
from app.schema.orm.core.user import User


class SurveyMembersService:
    """Service for survey membership role assignment management."""

    def _require_survey(self, db: Session, *, project_id: int, survey_id: int) -> None:
        ensure_present(
            sr.get_survey(db, project_id=project_id, survey_id=survey_id),
            error=SurveyNotFoundError(survey_id, project_id),
        )

    def _require_membership(self, db: Session, *, project_id: int, membership_id: int):  # type: ignore[return]
        return ensure_present(
            mr.get_by_id(db, membership_id=membership_id, project_id=project_id),
            error=MemberNotFoundError(),
        )

    def _require_survey_role(self, db: Session, *, project_id: int, role_id: int):  # type: ignore[return]
        return ensure_present(
            srr.get_by_id(db, role_id=role_id, project_id=project_id),
            error=SurveyRoleNotFoundError(),
        )

    def _require_assignment(
        self, db: Session, *, project_id: int, survey_id: int, membership_id: int
    ) -> SurveyMembershipRole:
        assignment = smr.get_by_membership(
            db, project_id=project_id, survey_id=survey_id, membership_id=membership_id
        )
        return ensure_present(assignment, error=SurveyMemberRoleNotFoundError())

    def list_survey_members(
        self,
        db: Session,
        *,
        project_id: int,
        survey_id: int,
        actor: User,  # noqa: ARG002
    ) -> list[SurveyMembershipRole]:
        self._require_survey(db, project_id=project_id, survey_id=survey_id)
        return smr.list_by_survey(db, project_id=project_id, survey_id=survey_id)

    def assign_member_role(
        self,
        db: Session,
        *,
        project_id: int,
        survey_id: int,
        data: AssignSurveyMemberRoleRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyMembershipRole:
        self._require_survey(db, project_id=project_id, survey_id=survey_id)
        self._require_membership(db, project_id=project_id, membership_id=data.membership_id)
        self._require_survey_role(db, project_id=project_id, role_id=data.role_id)

        existing = smr.get_by_membership(
            db, project_id=project_id, survey_id=survey_id, membership_id=data.membership_id
        )
        if existing is not None:
            raise SurveyMemberRoleAlreadyAssignedError()

        assignment = smr.create_assignment(
            db,
            project_id=project_id,
            survey_id=survey_id,
            membership_id=data.membership_id,
            role_id=data.role_id,
        )
        commit_with_err_handle(db)
        return assignment

    def update_member_role(
        self,
        db: Session,
        *,
        project_id: int,
        survey_id: int,
        membership_id: int,
        data: UpdateSurveyMemberRoleRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyMembershipRole:
        self._require_survey(db, project_id=project_id, survey_id=survey_id)
        self._require_survey_role(db, project_id=project_id, role_id=data.role_id)
        assignment = self._require_assignment(
            db, project_id=project_id, survey_id=survey_id, membership_id=membership_id
        )
        updated = smr.update_assignment(db, assignment, role_id=data.role_id)
        commit_with_err_handle(db)
        return updated

    def remove_member_role(
        self,
        db: Session,
        *,
        project_id: int,
        survey_id: int,
        membership_id: int,
        actor: User,  # noqa: ARG002
    ) -> None:
        self._require_survey(db, project_id=project_id, survey_id=survey_id)
        assignment = self._require_assignment(
            db, project_id=project_id, survey_id=survey_id, membership_id=membership_id
        )
        smr.delete_assignment(db, assignment)
        commit_with_err_handle(db)


survey_members_service = SurveyMembersService()
