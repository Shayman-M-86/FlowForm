from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain.errors import ProjectNotFoundError
from app.domain.permissions import PERMISSIONS
from app.repositories import projects_repo
from app.schema.api.requests.projects import CreateProjectRequest, UpdateProjectRequest
from app.schema.orm.core.project import Project
from app.schema.orm.core.user import User
from app.services.access.access_service import require_project_permission


class ProjectService:
    """Service for project operations."""

    def _get_project(self, db: Session, project_id: int) -> Project:
        """Fetch a project by ID without membership filtering.

        Used internally by mutation methods that already gate on
        @require_project_permission before reaching this point.
        """
        project = projects_repo.get_project_by_id(db, project_id)
        if project is None:
            raise ProjectNotFoundError(project_id=project_id)
        return project

    def list_projects(self, db: Session, *, actor: User) -> list[Project]:
        return projects_repo.list_projects(db, user_id=actor.id)

    def get_project(self, db: Session, *, project_id: int, actor: User) -> Project:
        project = projects_repo.get_project(db, project_id, user_id=actor.id)
        if project is None:
            raise ProjectNotFoundError(project_id=project_id)
        return project

    def get_project_by_slug(self, db: Session, *, project_slug: str, actor: User) -> Project:
        project = projects_repo.get_project_by_slug(db, project_slug, user_id=actor.id)
        if project is None:
            raise ProjectNotFoundError(project_slug=project_slug)
        return project

    def create_project(
        self,
        db: Session,
        data: CreateProjectRequest,
        actor: User
    ) -> Project:
        project = projects_repo.create_project(db, data, created_by_user_id=actor.id)
        commit_with_err_handle(db)
        return project

    @require_project_permission(PERMISSIONS.project.edit)
    def update_project(self, db: Session, *, project_id: int, data: UpdateProjectRequest, actor: User) -> Project:  # noqa: ARG002
        project = self._get_project(db, project_id)
        updated = projects_repo.update_project(db, project, data)
        commit_with_err_handle(db)
        return updated

    @require_project_permission(PERMISSIONS.project.delete)
    def delete_project(self, db: Session, *, project_id: int, actor: User) -> None:  # noqa: ARG002
        project = self._get_project(db, project_id)
        projects_repo.delete_project(db, project)
        commit_with_err_handle(db)
