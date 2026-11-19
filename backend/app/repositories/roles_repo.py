from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.permission import Permission
from app.schema.orm.core.project import ProjectRole
from app.schema.types import ProjectId, ProjectRoleId, RoleDescription, RoleName


def list_by_project(db: Session, project_id: ProjectId) -> list[ProjectRole]:
    return list(
        db.scalars(
            select(ProjectRole)
            .options(selectinload(ProjectRole.permissions))
            .where(ProjectRole.project_id == project_id)
            .order_by(ProjectRole.created_at.asc())
        )
    )


def get_by_id(db: Session, *, role_id: ProjectRoleId, project_id: ProjectId) -> ProjectRole | None:
    return db.scalar(
        select(ProjectRole)
        .options(selectinload(ProjectRole.permissions))
        .where(ProjectRole.id == role_id, ProjectRole.project_id == project_id)
    )


def create_role(
    db: Session,
    *,
    project_id: ProjectId,
    name: RoleName,
    description: RoleDescription | None,
    permissions: list[Permission],
) -> ProjectRole:
    role = ProjectRole(project_id=project_id, name=name, description=description)
    role.permissions = permissions
    db.add(role)
    flush_with_err_handle(db, contexts=[role])
    return role


def update_role(
    db: Session,
    role: ProjectRole,
    *,
    fields_set: set[str],
    name: RoleName | None,
    description: RoleDescription | None,
    permissions: list[Permission] | None,
) -> ProjectRole:
    if "name" in fields_set and name is not None:
        role.name = name
    if "description" in fields_set:
        role.description = description
    if "permissions" in fields_set and permissions is not None:
        role.permissions = permissions
    flush_with_err_handle(db, contexts=[role])
    return role


def delete_role(db: Session, role: ProjectRole) -> None:
    db.delete(role)
    flush_with_err_handle(db, contexts=[role])
