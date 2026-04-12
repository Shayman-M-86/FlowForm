from sqlalchemy.orm import Session

from app.api.v1.projects import project_service
from app.schema.orm.core.project import Project
from app.schema.orm.core.user import User


def resolve_project_ref(db: Session, ref: str, actor: User) -> Project:
    """Resolve a project URL segment that is either an integer ID or a slug.

    Tries to parse ``ref`` as an integer first. If that succeeds, fetches the
    project by ID (with membership filter). If it fails, fetches by slug
    (also with membership filter). Raises ProjectNotFoundError if the project
    does not exist or the actor is not a member.

    Returns the resolved Project so callers can use it directly rather than
    doing a second lookup.
    """
    try:
        project_id = int(ref)
        return project_service.get_project(db, project_id=project_id, actor=actor)
    except ValueError:
        return project_service.get_project_by_slug(db, project_slug=ref, actor=actor)
