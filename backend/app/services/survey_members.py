from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain.errors import (
    MemberNotFoundError,
    SurveyMemberRoleAlreadyAssignedError,
    SurveyMemberRoleNotFoundError,
    SurveyNotFoundError,
    SurveyRoleNotFoundError,
)
from app.domain.permissions import PERMISSIONS
from app.repositories import members_repo, survey_members_repo, survey_roles_repo, surveys_repo
from app.schema.api.requests.surveys_access import AssignSurveyMemberRoleRequest, UpdateSurveyMemberRoleRequest
from app.schema.orm.core.survey_access import SurveyMembershipRole
from app.schema.orm.core.user import User
from app.services.access.access_service import require_project_permission


class SurveyMembersService:
    """Service for survey membership role assignment management."""

    def _require_survey(self, db: Session, *, project_id: int, survey_id: int) -> None:
        if surveys_repo.get_survey(db, project_id=project_id, survey_id=survey_id) is None:
            raise SurveyNotFoundError(survey_id, project_id)

    def _require_membership(self, db: Session, *, project_id: int, membership_id: int):  # type: ignore[return]
        membership = members_repo.get_by_id(db, membership_id=membership_id, project_id=project_id)
        if membership is None:
            raise MemberNotFoundError()
        return membership

    def _require_survey_role(self, db: Session, *, project_id: int, role_id: int):  # type: ignore[return]
        role = survey_roles_repo.get_by_id(db, role_id=role_id, project_id=project_id)
        if role is None:
            raise SurveyRoleNotFoundError()
        return role

    def _require_assignment(
        self, db: Session, *, project_id: int, survey_id: int, membership_id: int
    ) -> SurveyMembershipRole:
        assignment = survey_members_repo.get_by_membership(
            db, project_id=project_id, survey_id=survey_id, membership_id=membership_id
        )
        if assignment is None:
            raise SurveyMemberRoleNotFoundError()
        return assignment

    @require_project_permission(PERMISSIONS.project.manage_members)
    def list_survey_members(
        self,
        db: Session,
        *,
        project_id: int,
        survey_id: int,
        actor: User,  # noqa: ARG002
    ) -> list[SurveyMembershipRole]:
        self._require_survey(db, project_id=project_id, survey_id=survey_id)
        return survey_members_repo.list_by_survey(db, project_id=project_id, survey_id=survey_id)

    @require_project_permission(PERMISSIONS.project.manage_members)
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

        existing = survey_members_repo.get_by_membership(
            db, project_id=project_id, survey_id=survey_id, membership_id=data.membership_id
        )
        if existing is not None:
            raise SurveyMemberRoleAlreadyAssignedError()

        assignment = survey_members_repo.create_assignment(
            db,
            project_id=project_id,
            survey_id=survey_id,
            membership_id=data.membership_id,
            role_id=data.role_id,
        )
        commit_with_err_handle(db)
        return assignment

    @require_project_permission(PERMISSIONS.project.manage_members)
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
        updated = survey_members_repo.update_assignment(db, assignment, role_id=data.role_id)
        commit_with_err_handle(db)
        return updated

    @require_project_permission(PERMISSIONS.project.manage_members)
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
        survey_members_repo.delete_assignment(db, assignment)
        commit_with_err_handle(db)


survey_members_service = SurveyMembersService()
