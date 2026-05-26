from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain.errors import ProjectRoleNotFoundError, ProjectRoleSystemProtectedError
from app.domain.permissions import PERMISSIONS
from app.repositories import permissions_repo, roles_repo
from app.schema.api.requests.projects import CreateProjectRoleRequest, UpdateProjectRoleRequest
from app.schema.orm.core.project import ProjectRole
from app.schema.orm.core.user import User
from app.services.access.access_service import require_project_permission


class RolesService:
    """Service for project role management."""

    def _get_role(self, db: Session, *, role_id: int, project_id: int) -> ProjectRole:
        role = roles_repo.get_by_id(db, role_id=role_id, project_id=project_id)
        if role is None:
            raise ProjectRoleNotFoundError()
        return role


    def list_project_roles(
        self, db: Session, *, project_id: int, actor: User  # noqa: ARG002
    ) -> list[ProjectRole]:
        return roles_repo.list_by_project(db, project_id)

    @require_project_permission(PERMISSIONS.project.manage_roles)
    def create_role(
        self, db: Session, *, project_id: int, data: CreateProjectRoleRequest, actor: User  # noqa: ARG002
    ) -> ProjectRole:
        permission_rows = permissions_repo.get_permissions_by_names(db, data.permissions)
        role = roles_repo.create_role(
            db,
            project_id=project_id,
            name=data.name,
            permissions=permission_rows,
        )
        commit_with_err_handle(db)
        return role

    @require_project_permission(PERMISSIONS.project.manage_roles)
    def update_role(
        self, db: Session, *, project_id: int, role_id: int, data: UpdateProjectRoleRequest, actor: User  # noqa: ARG002
    ) -> ProjectRole:
        role = self._get_role(db, role_id=role_id, project_id=project_id)
        if role.is_system_role:
            raise ProjectRoleSystemProtectedError()
        permission_rows = (
            permissions_repo.get_permissions_by_names(db, data.permissions)
            if "permissions" in data.model_fields_set and data.permissions is not None
            else None
        )
        role = roles_repo.update_role(
            db,
            role,
            fields_set=data.model_fields_set,
            name=data.name,
            permissions=permission_rows,
        )
        commit_with_err_handle(db)
        return role

    @require_project_permission(PERMISSIONS.project.manage_roles)
    def delete_role(
        self, db: Session, *, project_id: int, role_id: int, actor: User  # noqa: ARG002
    ) -> None:
        role = self._get_role(db, role_id=role_id, project_id=project_id)
        if role.is_system_role:
            raise ProjectRoleSystemProtectedError()
        roles_repo.delete_role(db, role)
        commit_with_err_handle(db)


roles_service = RolesService()
