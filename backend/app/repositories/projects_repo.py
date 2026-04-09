from sqlalchemy.orm import Session

from app.schema.api.requests.projects import CreateProjectRequest
from app.schema.orm.core.project import Project


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
    db.flush()
    return project
