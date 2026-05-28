from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.survey_access import SurveyRole


def list_by_project(db: Session, project_id: int) -> list[SurveyRole]:
    return list(
        db.scalars(
            select(SurveyRole)
            .options(selectinload(SurveyRole.permissions))
            .where(SurveyRole.project_id == project_id)
            .order_by(SurveyRole.created_at.asc())
        )
    )


def get_by_id(db: Session, *, role_id: int, project_id: int) -> SurveyRole | None:
    return db.scalar(
        select(SurveyRole)
        .options(selectinload(SurveyRole.permissions))
        .where(SurveyRole.id == role_id, SurveyRole.project_id == project_id)
    )


def create_role(
    db: Session,
    *,
    project_id: int,
    name: str,
    description: str | None,
    permissions: list,
) -> SurveyRole:
    role = SurveyRole(project_id=project_id, name=name, description=description)
    role.permissions = permissions
    db.add(role)
    flush_with_err_handle(db, contexts=[role])
    return role


def update_role(
    db: Session,
    role: SurveyRole,
    *,
    fields_set: set[str],
    name: str | None,
    description: str | None,
    permissions: list | None,
) -> SurveyRole:
    if "name" in fields_set and name is not None:
        role.name = name
    if "description" in fields_set:
        role.description = description
    if "permissions" in fields_set and permissions is not None:
        role.permissions = permissions
    flush_with_err_handle(db, contexts=[role])
    return role


def delete_role(db: Session, role: SurveyRole) -> None:
    db.delete(role)
    flush_with_err_handle(db, contexts=[role])
