"""Whole-document updates for editable survey versions."""

from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain import survey_rules, version_rules
from app.domain.errors import VersionNotFoundError
from app.domain.guards import ensure_present
from app.repositories import surveys_repo
from app.schema.models.survey_document import SurveyDefinition
from app.schema.orm.core.survey import SurveyVersion
from app.schema.types import ProjectId, SurveyId, SurveyVersionNumber


class ContentService:
    """Apply content changes to a draft's complete survey definition."""

    def update_definition(
        self,
        db: Session,
        *,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: SurveyVersionNumber,
        definition: SurveyDefinition,
    ) -> SurveyVersion:
        """Replace an editable version's definition and commit the update.

        The caller's survey-permission guard owns authorization. Definition
        shape validation uses the shared SurveyDefinition before this call.
        """
        version = ensure_present(
            surveys_repo.get_version(db, project_id, survey_id, version_number),
            error=VersionNotFoundError(survey_id=survey_id, version_number=version_number),
        )
        version_rules.ensure_is_editable(version=version)
        updated = surveys_repo.update_definition(db, version, survey_rules.validate_definition(definition))
        commit_with_err_handle(db, contexts=[updated])
        return updated
