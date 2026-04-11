from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.api.requests.projects import CreateProjectRequest, UpdateProjectRequest
from app.schema.orm.core.project import Project, ProjectMembership


def list_projects(db: Session, user_id: int) -> list[Project]:
    return list(
        db.scalars(
            select(Project)
            .join(ProjectMembership, ProjectMembership.project_id == Project.id)
            .where(ProjectMembership.user_id == user_id)
        )
    )


def get_project(db: Session, project_id: int, user_id: int) -> Project | None:
    """Fetch a project only if the given user is a member."""
    return db.scalar(
        select(Project)
        .join(ProjectMembership, ProjectMembership.project_id == Project.id)
        .where(Project.id == project_id, ProjectMembership.user_id == user_id)
    )


def get_project_by_slug(db: Session, slug: str, user_id: int) -> Project | None:
    """Fetch a project by slug only if the given user is a member."""
    return db.scalar(
        select(Project)
        .join(ProjectMembership, ProjectMembership.project_id == Project.id)
        .where(Project.slug == slug, ProjectMembership.user_id == user_id)
    )


def get_project_by_id(db: Session, project_id: int) -> Project | None:
    """Fetch a project by ID with no membership filter.

    Use only in contexts where membership has already been verified
    (e.g. after @require_project_permission has passed).
    """
    return db.scalar(select(Project).where(Project.id == project_id))


def create_project(
    db: Session,
    data: CreateProjectRequest,
    created_by_user_id: int | None = None,
) -> Project:
    project = Project(
        name=data.name,
        slug=data.slug,
        created_by_user_id=created_by_user_id,
    )
    db.add(project)
    flush_with_err_handle(db, contexts=[project])

    if created_by_user_id is not None:
        membership = ProjectMembership(user_id=created_by_user_id, project_id=project.id)
        db.add(membership)

    return project


def update_project(db: Session, project: Project, data: UpdateProjectRequest) -> Project:
    if data.name is not None:
        project.name = data.name
    if data.slug is not None:
        project.slug = data.slug
    flush_with_err_handle(db, contexts=[project])
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    flush_with_err_handle(db, contexts=[project])
