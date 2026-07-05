from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain.errors import ProjectNotFoundError
from app.domain.guards import ensure_present
from app.repositories import projects_repo as pr
from app.schema.api.requests.projects import CreateProjectRequest, UpdateProjectRequest
from app.schema.orm.core.project import Project
from app.schema.orm.core.user import User


class ProjectService:
    """Service for project operations."""

    def _get_project(self, db: Session, project_id: int) -> Project:
        """Fetch a project by ID without membership filtering.

        Used internally by mutation methods that already gate on
        @require_project_permission before reaching this point.
        """
        return ensure_present(
            pr.get_project_by_id(db, project_id),
            error=ProjectNotFoundError(project_id=project_id),
        )

    def list_projects(self, db: Session, *, actor: User) -> list[Project]:
        return pr.list_projects(db, user_id=actor.id)

    def get_project(self, db: Session, *, project_id: int, actor: User) -> Project:
        return ensure_present(
            pr.get_project(db, project_id, user_id=actor.id),
            error=ProjectNotFoundError(project_id=project_id),
        )

    def get_project_by_slug(self, db: Session, *, project_slug: str, actor: User) -> Project:
        return ensure_present(
            pr.get_project_by_slug(db, project_slug, user_id=actor.id),
            error=ProjectNotFoundError(project_slug=project_slug),
        )

    def create_project(
        self,
        db: Session,
        data: CreateProjectRequest,
        actor: User
    ) -> Project:
        project = pr.create_project(db, data, created_by_user_id=actor.id)
        commit_with_err_handle(db)
        return project

    def update_project(self, db: Session, *, project_id: int, data: UpdateProjectRequest, actor: User) -> Project:  # noqa: ARG002
        project = self._get_project(db, project_id)
        updated = pr.update_project(db, project, data)
        commit_with_err_handle(db)
        return updated

    def delete_project(self, db: Session, *, project_id: int, actor: User) -> None:  # noqa: ARG002
        project = self._get_project(db, project_id)
        pr.delete_project(db, project)
        commit_with_err_handle(db)
