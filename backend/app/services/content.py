"""Whole-content updates for editable survey versions."""

from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain import version_rules
from app.domain.errors import SurveyVersionIdNotFoundError, VersionRevisionConflictError
from app.domain.guards import ensure_present
from app.repositories import surveys_repo
from app.schema.models.survey_document import SurveyContent
from app.schema.types import DocumentRevision, ProjectId, SurveyId, SurveyVersionId


class ContentService:
    """Replace the authored content of an editable survey version."""

    def save_content(
        self,
        db: Session,
        *,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_id: SurveyVersionId,
        expected_revision: DocumentRevision,
        content: SurveyContent,
    ) -> DocumentRevision:
        """Save the next revision after checking the editor's revision under lock."""
        version = ensure_present(
            surveys_repo.lock_version_by_id(db, project_id, survey_id, version_id),
            error=SurveyVersionIdNotFoundError(),
        )
        version_rules.ensure_is_editable(version=version)
        if version.revision != expected_revision:
            raise VersionRevisionConflictError(expected_revision=expected_revision, current_revision=version.revision)

        revision = version.revision + 1
        surveys_repo.update_content(db, version, content, revision)
        commit_with_err_handle(db, contexts=[version])
        return revision
