from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.project import ProjectMembership


def list_by_project(db: Session, project_id: int) -> list[ProjectMembership]:
    return list(
        db.scalars(
            select(ProjectMembership)
            .options(selectinload(ProjectMembership.user))
            .where(ProjectMembership.project_id == project_id)
            .order_by(ProjectMembership.created_at.asc())
        )
    )


def get_by_user_and_project(
    db: Session, *, user_id: int, project_id: int
) -> ProjectMembership | None:
    return db.scalar(
        select(ProjectMembership).where(
            ProjectMembership.user_id == user_id,
            ProjectMembership.project_id == project_id,
        )
    )


def get_by_id(db: Session, *, membership_id: int, project_id: int) -> ProjectMembership | None:
    return db.scalar(
        select(ProjectMembership)
        .options(selectinload(ProjectMembership.user), selectinload(ProjectMembership.role))
        .where(
            ProjectMembership.id == membership_id,
            ProjectMembership.project_id == project_id,
        )
    )


def update_membership(
    db: Session,
    membership: ProjectMembership,
    *,
    fields_set: set[str],
    role_id: int | None,
    status: str | None,
) -> ProjectMembership:
    if "role_id" in fields_set:
        membership.role_id = role_id
    if "status" in fields_set and status is not None:
        membership.status = status
    flush_with_err_handle(db, contexts=[membership])
    return membership


def delete_membership(db: Session, membership: ProjectMembership) -> None:
    db.delete(membership)
    flush_with_err_handle(db, contexts=[membership])


def create_membership(
    db: Session,
    *,
    project_id: int,
    user_id: int,
    role_id: int | None,
) -> ProjectMembership:
    membership = ProjectMembership(
        project_id=project_id,
        user_id=user_id,
        role_id=role_id,
    )
    db.add(membership)
    flush_with_err_handle(db, contexts=[membership])
    return membership
