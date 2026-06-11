from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain.errors import SurveyRoleNotFoundError
from app.domain.guards import ensure_present
from app.repositories import permissions_repo as per
from app.repositories import survey_roles_repo as srr
from app.schema.api.requests.surveys_access import CreateSurveyRoleRequest, UpdateSurveyRoleRequest
from app.schema.orm.core.survey_access import SurveyRole
from app.schema.orm.core.user import User


class SurveyRolesService:
    """Service for survey role management."""

    def _get_role(self, db: Session, *, role_id: int, project_id: int) -> SurveyRole:
        return ensure_present(
            srr.get_by_id(db, role_id=role_id, project_id=project_id),
            error=SurveyRoleNotFoundError(),
        )

    def list_survey_roles(
        self, db: Session, *, project_id: int, actor: User  # noqa: ARG002
    ) -> list[SurveyRole]:
        return srr.list_by_project(db, project_id)

    def create_role(
        self, db: Session, *, project_id: int, data: CreateSurveyRoleRequest, actor: User  # noqa: ARG002
    ) -> SurveyRole:
        permission_rows = per.get_permissions_by_names(db, data.permissions)
        role = srr.create_role(
            db,
            project_id=project_id,
            name=data.name,
            description=data.description,
            permissions=permission_rows,
        )
        commit_with_err_handle(db)
        return role

    def update_role(
        self,
        db: Session,
        *,
        project_id: int,
        role_id: int,
        data: UpdateSurveyRoleRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyRole:
        role = self._get_role(db, role_id=role_id, project_id=project_id)
        permission_rows = (
            per.get_permissions_by_names(db, data.permissions)
            if "permissions" in data.model_fields_set and data.permissions is not None
            else None
        )
        role = srr.update_role(
            db,
            role,
            fields_set=data.model_fields_set,
            name=data.name,
            description=data.description,
            permissions=permission_rows,
        )
        commit_with_err_handle(db)
        return role

    def delete_role(
        self, db: Session, *, project_id: int, role_id: int, actor: User  # noqa: ARG002
    ) -> None:
        role = self._get_role(db, role_id=role_id, project_id=project_id)
        srr.delete_role(db, role)
        commit_with_err_handle(db)


survey_roles_service = SurveyRolesService()
