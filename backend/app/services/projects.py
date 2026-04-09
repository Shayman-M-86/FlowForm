from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.transaction import commit_or_rollback
from app.domain.errors import ProjectSlugConflictError
from app.repositories import projects_repo
from app.schema.api.requests.projects import CreateProjectRequest
from app.schema.orm.core.project import Project


class ProjectService:
    def create_project(
        self,
        db: Session,
        data: CreateProjectRequest,
        created_by_user_id: int | None = None,
    ) -> Project:
        try:
            project = projects_repo.create_project(db, data, created_by_user_id)
            commit_or_rollback(db)
        except IntegrityError as exc:
            if isinstance(exc.orig, UniqueViolation) and "slug" in (exc.orig.diag.constraint_name or ""):
                raise ProjectSlugConflictError() from None
            raise
        return project
