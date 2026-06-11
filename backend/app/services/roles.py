from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain.errors import ProjectRoleNotFoundError, ProjectRoleSystemProtectedError
from app.domain.guards import ensure_present
from app.repositories import permissions_repo as per
from app.repositories import roles_repo as rr
from app.schema.api.requests.projects import CreateProjectRoleRequest, UpdateProjectRoleRequest
from app.schema.orm.core.project import ProjectRole
from app.schema.orm.core.user import User


class RolesService:
    """Service for project role management."""

    def _get_role(self, db: Session, *, role_id: int, project_id: int) -> ProjectRole:
        return ensure_present(
            rr.get_by_id(db, role_id=role_id, project_id=project_id),
            error=ProjectRoleNotFoundError(),
        )

    def list_project_roles(
        self, db: Session, *, project_id: int, actor: User  # noqa: ARG002
    ) -> list[ProjectRole]:
        return rr.list_by_project(db, project_id)

    def create_role(
        self, db: Session, *, project_id: int, data: CreateProjectRoleRequest, actor: User  # noqa: ARG002
    ) -> ProjectRole:
        permission_rows = per.get_permissions_by_names(db, data.permissions)
        role = rr.create_role(
            db,
            project_id=project_id,
            name=data.name,
            description=data.description,
            permissions=permission_rows,
        )
        commit_with_err_handle(db)
        return role

    def update_role(
        self, db: Session, *, project_id: int, role_id: int, data: UpdateProjectRoleRequest, actor: User  # noqa: ARG002
    ) -> ProjectRole:
        role = self._get_role(db, role_id=role_id, project_id=project_id)
        if role.is_system_role:
            raise ProjectRoleSystemProtectedError()
        permission_rows = (
            per.get_permissions_by_names(db, data.permissions)
            if "permissions" in data.model_fields_set and data.permissions is not None
            else None
        )
        role = rr.update_role(
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
        if role.is_system_role:
            raise ProjectRoleSystemProtectedError()
        rr.delete_role(db, role)
        commit_with_err_handle(db)


roles_service = RolesService()
